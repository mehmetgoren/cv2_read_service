from typing import List

from common.data.source_model import SourceModel
from common.data.source_repository import SourceRepository
from common.utilities import logger, crate_redis_connection, RedisDb
from common.data.heartbeat_repository import HeartbeatRepository
from core.source_reader import start


# def get_id():
#     val = shortuuid.uuid()[:11]
#     return val

def check_sources() -> List[SourceModel]:
    # user = 'admin'
    # pwd = 'a12345678'
    # ip = '192.168.0.108'
    # total_camera_count = 5
    # for j in range(total_camera_count):
    #     rep.add(DahuaDvrRtspModel(get_id(), j + 1, user, pwd, ip))

    connection = crate_redis_connection(RedisDb.MAIN)
    rep = SourceRepository(connection)
    # # rep.flush_db()
    #
    # source = Source(get_id(), 'Concord IPC', 'concord', ConcordIpcRtspModel(get_id(), 'concord', 'admin', 'admin123456',
    #                                                                         '192.168.0.19').create_rtsp_address())
    # rep.add(source)
    #
    # source = Source(get_id(), 'Anker Eufy Security 2K', 'anker eufy',
    #                 AnkerEufyModel(get_id(), 'anker eufy', 'Admin1', 'Admin1', '192.168.0.15').create_rtsp_address())
    # rep.add(source)
    #
    # camera_count = 5
    # ip_start = 26
    # for j in range(camera_count):
    #     source = Source(get_id(), 'Tapo C200 1080P', f'tapo 200 ({j + 1})',
    #                     TapoC200(get_id(), f'tapo 200 ({j + 1})', 'admin12', 'admin12',
    #                              f'192.168.0.{ip_start + j}').create_rtsp_address())
    #     rep.add(source)

    sources = rep.get_all()
    for source in sources:
        print(source.address)
    return sources


def main():
    service_name = 'cv2_read_service'
    heartbeat = HeartbeatRepository(crate_redis_connection(RedisDb.MAIN), service_name)
    heartbeat.start()
    if len(check_sources()) == 0:
        logger.warning(f'No source has been found for {service_name}, which is now is exiting...')
    logger.info(f'{service_name} will start soon')
    start()


if __name__ == '__main__':
    main()
