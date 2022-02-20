from redis import Redis


class FailedRepository:
    def __init__(self, connection: Redis):
        self.namespace_read = 'failed:read:'
        self.connection: Redis = connection

    def _get_read_key(self, name: str, rtsp_address: str):
        key = f'{name}_{rtsp_address}'
        return f'{self.namespace_read}{key}'

    def add_read(self, name: str, rtsp_address: str):
        key = self._get_read_key(name, rtsp_address)
        self.connection.incr(key)
