import base64
import json
import os
import signal

import numpy as np
import psutil
import time
from multiprocessing import Process
import cv2
from rq import Queue, Connection, Worker, Retry, get_current_job
from rq.command import send_stop_job_command, send_kill_horse_command, send_shutdown_command
from rq.job import Job
from datetime import datetime
import asyncio
from typing import List

from common.data.service_repository import ServiceRepository
from common.event_bus.event_bus import EventBus
from common.utilities import logger, config, crate_redis_connection, RedisDb
from common.data.source_repository import SourceRepository
from core.data.jober_repository import Jober, JoberRepository
from core.data.failed_repository import FailedRepository
from core.sources import Cv2RtspSource, SourceBase

_connection_main = crate_redis_connection(RedisDb.MAIN)
_connection_rq = crate_redis_connection(RedisDb.RQ2)
_queue = Queue(connection=_connection_rq)
_source_repository = SourceRepository(_connection_main)
_jober_rep = JoberRepository(_connection_rq)
_failed_rep = FailedRepository(_connection_rq)
_event_bus = EventBus('read_service')
_checker_job_pid = {'pid': -1}


def _close_stream(source: SourceBase, name: str, rtsp_type: int):
    logger.error(f'camera {name} will not work anymore')
    try:
        source.close()
    except BaseException as e:
        rtsp_type_str = 'opencv' if rtsp_type == 0 else 'ffmpeg'
        logger.error(f'error while closing stream({rtsp_type_str}): {e}')
    logger.error(f'camera ({name}) has been stopped and it should work again with retry')


def _publish(img: np.array, name: str, identifier: str):
    img_str = base64.b64encode(cv2.imencode('.jpg', img)[1]).decode()
    dic = {'name': name, 'img': img_str, 'source': identifier}
    _event_bus.publish_async(json.dumps(dic, ensure_ascii=False, indent=4))
    logger.info(f'camera ({name}) -> an image has been send to broker at {datetime.now()}')


def _read(fps: int, buffer_size: int, name: str, rtsp_address: str, identifier: str):
    me_job = get_current_job()
    ex = None
    try:
        source = Cv2RtspSource(name, rtsp_address)
        source.set_buffer_size(buffer_size)
        prev = 0
        logger.info(f"cv2 source has been opened, capturing will be starting now, camera no:  {name}, url: {rtsp_address}")
        while not source.is_closed():
            time_elapsed = time.time() - prev
            img = source.get_img()
            if img is None:
                _close_stream(source, name, 0)
                break
            if time_elapsed > 1. / fps:
                prev = time.time()
                _publish(img, name, identifier)
    except BaseException as e:
        ex = e
    finally:
        # todo: do not add if a camera has been failed more than max specified
        # todo: implement it with them -> self.source_reader.max_retry: int = 150, self.source_reader.max_retry_in: int = 6  # hours
        time.sleep(5)
        model = Jober()
        model.job_id = me_job.id
        model.worker_name = me_job.worker_name
        model.worker_pid = os.getpid()
        model.starter_pid = psutil.Process(os.getpid()).ppid()
        model.args = f'{fps}º{buffer_size}º{name}º{rtsp_address}º{identifier}'
        model.exception_msg = str(ex) if ex is not None else ''
        _jober_rep.add(model)
        _failed_rep.add_read(name, rtsp_address)


def _start_worker():
    worker = Worker(['default'])
    worker.work(burst=True)


def _start_workers(jobs: List[Job]):
    logger.info(f'jobs count: {len(jobs)}')
    with Connection(connection=_connection_rq):
        for _ in jobs:
            proc = Process(target=_start_worker)
            # proc.daemon = daemon
            proc.start()
            time.sleep(1)


def _check_workers():
    _checker_job_pid['pid'] = os.getpid()
    while 1:
        not_working_jobs = _jober_rep.get_all()
        if len(not_working_jobs) > 0:
            for failed in not_working_jobs:
                logger.info(f'failed job has been detected, id: {failed.job_id}')

                try:
                    pid = int(failed.starter_pid)
                    p = psutil.Process(pid)
                    p.terminate()
                    time.sleep(1)
                    logger.info(f'starter process has been killed, pid: {pid}')
                except BaseException as ex:
                    logger.error(f'error while killing starter process command, job {failed.job_id}, err: {ex}')

                try:
                    _jober_rep.remove(failed)
                except BaseException as ex:
                    logger.error(f'error while removing jober, job {failed.job_id}, err: {ex}')

                try:
                    args = failed.args.split('º')
                    job = _queue.enqueue(_read, int(args[0]), int(args[1]), args[2], args[3], args[4],
                                         job_timeout=-1)
                    _start_workers([job])
                except BaseException as ex:
                    logger.error(f'error while requeue job {failed.job_id}, err: {ex}')
        else:
            logger.info(f'No failed jobs at {datetime.utcnow()}')
        time.sleep(1)


def _add_checker_job():
    retry = Retry(max=1000000)
    job = _queue.enqueue(_check_workers, job_timeout=-1, retry=retry)
    return job


def _delete_all():
    _connection_rq.flushdb()


def _init_cameras() -> (List[Job], BaseException):
    jobs: List[Job] = []
    err = None
    try:
        sources = _source_repository.get_all()
        for source in sources:
            name = source.get_name()
            rtsp_address = source.get_rtsp_address()
            fps, buffer_size = config.source_reader.fps, config.source_reader.buffer_size
            job = _queue.enqueue(_read, fps, buffer_size, name, rtsp_address, source.get_id(), job_timeout=-1)
            jobs.append(job)
    except BaseException as ex:
        logger.error(ex)
        err = ex
    if err is None:
        logger.info('all cameras have been initialized')
    return jobs, err


def _kill_process(op: str, pid: int):
    try:
        if psutil.pid_exists(pid):
            os.kill(pid, signal.SIGKILL)
    except BaseException as e:
        logger.error(f'an error occurred during killing {op} process rq command, err: {e}')


def _kill_all_previous_jobs():
    jobers = _jober_rep.get_all()
    for jober in jobers:
        try:
            if len(jober.job_id) > 0:
                send_stop_job_command(_connection_rq, jober.job_id)
        except BaseException as e:
            logger.error(f'an error occurred during the stopping rq command, worker: {jober.worker_name}, err: {e}')
        try:
            if len(jober.worker_name) > 0:
                send_kill_horse_command(_connection_rq, jober.worker_name)
        except BaseException as e:
            logger.error(f'an error occurred during the killing rq command, worker: {jober.worker_name}, err: {e}')
        try:
            if len(jober.worker_name) > 0:
                send_shutdown_command(_connection_rq, jober.worker_name)
        except BaseException as e:
            logger.error(f'an error occurred during the shutting-down rq command, op: {jober.worker_name}, err: {e}')
        _kill_process('starter process', jober.starter_pid)
        _kill_process('worker process', jober.worker_pid)


def start():
    _kill_all_previous_jobs()
    _delete_all()
    try:
        service_repository = ServiceRepository(_connection_main)
        service_repository.add('cv2_read_service', 'The The OpenCV Service®')
        checker_job = _add_checker_job()
        _start_workers([checker_job])
        jobs, err = _init_cameras()
        if err is not None:
            logger.error(f'error while initializing cameras: {err}, the operation will be terminated')
            return
        _start_workers(jobs)
        loop = asyncio.get_event_loop()
        loop.run_forever()
    finally:
        _kill_all_previous_jobs()
        _kill_process('checker job', _checker_job_pid['pid'])
        _delete_all()
