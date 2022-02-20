from redis import Redis
from typing import List


class Jober:
    def __init__(self):
        self.starter_pid = ''
        self.worker_pid = ''
        self.worker_name = ''
        self.job_id = ''
        self.args = ''
        self.exception_msg = ''


class JoberRepository:
    def __init__(self, connection: Redis):
        self.namespace = 'jober:'
        self.connection: Redis = connection

    def _get_key(self, model: Jober):
        key = model.job_id
        return f'{self.namespace}{key}'

    def add(self, model: Jober):
        key = self._get_key(model)
        dic = model.__dict__.copy()
        self.connection.hset(key, mapping=dic)

    def remove(self, model: Jober):
        key = self._get_key(model)
        self.connection.delete(key)

    def get_all(self) -> List[Jober]:
        models: List[Jober] = []
        keys = self.connection.keys(f'{self.namespace}*')
        for key in keys:
            dic = self.connection.hgetall(key)
            model = Jober()
            model.starter_pid = dic[b'starter_pid'].decode('utf-8')
            model.worker_pid = dic[b'worker_pid'].decode('utf-8')
            model.worker_name = dic[b'worker_name'].decode('utf-8')
            model.job_id = dic[b'job_id'].decode('utf-8')
            model.args = dic[b'args'].decode('utf-8')
            model.exception_msg = dic[b'exception_msg'].decode('utf-8')
            models.append(model)
        return models
