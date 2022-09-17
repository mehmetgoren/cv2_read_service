from abc import ABC, abstractmethod


class BaseRtspModel(ABC):
    @abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError('BaseRtspModel.get_id')

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError('BaseRtspModel.get_name')

    @abstractmethod
    def create_rtsp_address(self) -> str:
        raise NotImplementedError('BaseRtspModel.create_rtsp_address')


class GenericRtspModel(BaseRtspModel):
    def __init__(self, identifier: str, name: str, rtsp_address: str):
        self.id = identifier
        self.name = name
        self.rtsp_address = rtsp_address
        self.brand = 'Generic'

    def get_id(self) -> str:
        return self.id

    def get_name(self) -> str:
        return self.name

    def create_rtsp_address(self) -> str:
        return self.rtsp_address


class DahuaDvrRtspModel(BaseRtspModel):
    def __init__(self, identifier: str, camera_no: int, user: str, pwd: str, ip: str):
        self.id = identifier
        self.brand = 'Dahua DVR'
        self.name = str(camera_no)
        self.camera_no = camera_no
        self.user = user
        self.pwd = pwd
        self.ip = ip
        self.port = 554
        self.route = '/cam/realmonitor?channel'
        self.subtype = 0  # 0 is main stream, 1 is extra stream

    def get_id(self) -> str:
        return self.id

    def get_name(self) -> str:
        return self.name

    def create_rtsp_address(self) -> str:
        return f'rtsp://{self.user}:{self.pwd}@{self.ip}:{self.port}{self.route}={self.camera_no}&subtype={self.subtype}'


class ConcordIpcRtspModel(GenericRtspModel):
    def __init__(self, identifier: str, name: str, user: str, pwd: str, ip: str):
        super().__init__(identifier, name, f'rtsp://{user}:{pwd}@{ip}:{8554}/profile0')
        self.brand = 'Concord IPC 3MP'


class AnkerEufyModel(GenericRtspModel):
    def __init__(self, identifier: str, name: str, user: str, pwd: str, ip: str):
        super().__init__(identifier, name, f'rtsp://{user}:{pwd}@{ip}/live0')
        self.brand = 'Anker Eufy Security 2K'


class TapoC200(GenericRtspModel):
    def __init__(self, identifier: str, name: str, user: str, pwd: str, ip: str):
        super().__init__(identifier, name, f'rtsp://{user}:{pwd}@{ip}:554/stream1')
        self.brand = 'TP Link Tapo C200 1080P'


class HikVision(GenericRtspModel):
    def __init__(self, identifier: str, name: str, user: str, pwd: str, ip: str):
        super().__init__(identifier, name, f'rtsp://{user}:{pwd}@{ip}:554/Streaming/Channels/101')
        self.brand = 'HIKVISION LTD'
