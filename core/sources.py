import os
import queue
import threading
from abc import ABC, abstractmethod
import cv2
import numpy as np

from common.utilities import logger


class SourceBase(ABC):

    @abstractmethod
    def get_img(self) -> np.array:
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        pass

    @abstractmethod
    def close(self):
        pass


class ImageFolderSource(SourceBase):
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.img_dirs = os.path.expanduser(folder_path)
        self.listdir = os.listdir(self.img_dirs)
        self.count = len(self.listdir)
        self.current_index = 0

    def get_img(self) -> np.array:
        if self.is_closed():
            return None
        current_file = os.path.join(self.img_dirs, self.listdir[self.current_index])
        img = cv2.imread(current_file)
        self.current_index += 1
        return img

    def is_closed(self) -> bool:
        return self.count <= self.current_index

    def close(self):
        pass


class SimpleWebcamSource(SourceBase):
    def __init__(self, cam_id: int = 0):
        self.cam_id = cam_id
        self.cam = cv2.VideoCapture(cam_id)

    def set_fps(self, fps: int):
        self.cam.set(cv2.CAP_PROP_FPS, fps)

    def get_img(self) -> np.array:
        ret_val, numpy_img = self.cam.read()
        return numpy_img

    def is_closed(self) -> bool:
        try:
            return not self.cam.isOpened()
        except Exception as ex:
            logger.error(f'unexpected error on close check (camera {self.cam_id}), details: {ex}')
            return True

    def close(self):
        try:
            self.cam.release()
            # cv2.destroyAllWindows()  # ???
        except BaseException as ex:
            logger.error(f'(camera {self.cam_id}) -> An error occurred while releasing a video capture, details: {ex}')
        self.cam = None


class VideoCaptureDaemon(threading.Thread):
    def __init__(self, address: str, result_queue: queue.Queue):
        super().__init__()
        self.daemon = True
        self.address = address
        self.result_queue = result_queue

    def run(self):
        self.result_queue.put(cv2.VideoCapture(self.address))


# do not catch any exception. RQ retry mechanism will take care of it
class Cv2RtspSource(SourceBase):
    def __init__(self, name: str, rtsp_address: str):
        self.name = name
        self.rtsp_address = rtsp_address
        self.timeout = 10
        self.is_capturing_working = True
        self.cam = self.get_video_capture()  # cv2.VideoCapture(rtsp_address)
        self.type_name = None

    def get_video_capture(self):
        result_queue = queue.Queue()
        VideoCaptureDaemon(self.rtsp_address, result_queue).start()
        try:
            return result_queue.get(block=True, timeout=self.timeout)
        except queue.Empty:
            logger.error(
                f'camera ({self.name}) cv2.VideoCapture: could not grab input ({self.rtsp_address}). Timeout occurred after {self.timeout}s')
            self.is_capturing_working = False
            return None

    def set_fps(self, fps: int):
        # self.cam.set(cv2.CAP_PROP_FPS, fps if fps <= 5.0 else 5.0)
        self.cam.set(cv2.CAP_PROP_FPS, fps)

    def set_buffer_size(self, size: int):
        self.cam.set(cv2.CAP_PROP_BUFFERSIZE, size)

    def get_img(self) -> np.array:
        if not self.is_capturing_working:
            return None
        succeed, numpy_img = self.cam.read()
        if not succeed or numpy_img is None:
            logger.error(f'camera ({self.name}) could not capture any frame and is now being released')
            return None
        else:
            return numpy_img

    def is_closed(self) -> bool:
        return not self.cam.isOpened()

    def close(self):
        self.cam.release()

    # todo open it for jetson nano
    # def set_open_cv_size(self):
    #     self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    #     self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
