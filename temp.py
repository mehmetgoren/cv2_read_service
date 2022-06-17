import base64
from datetime import datetime
from io import BytesIO
import cv2
from PIL import Image  # info: PIL was added only for this benchmarking
from numpy import asarray


def bench_pil_vs_cv2():
    img_path = '/home/gokalp/Downloads/download (43)'
    image = Image.open(img_path)
    numpy_img = asarray(image)
    # To convert RGB to BGR
    # numpy_img = numpy_img[:, :, ::-1]

    img_str = ''
    length = 100
    start = datetime.now()
    for j in range(length):
        buff = cv2.imencode('.jpg', numpy_img)[1]
        img_str = base64.b64encode(buff).decode()
        # print(len(img_str))
    end = datetime.now()
    print(f'cv2 length: {len(img_str)}')
    print(f'cv2 ms: {(end - start).microseconds}')

    start = datetime.now()
    for j in range(length):
        img = Image.fromarray(numpy_img)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        # print(len(img_str))
    end = datetime.now()
    print(f'PIL length: {len(img_str)}')
    print(f'PIL ms: {(end - start).microseconds}')
    # result:
    # cv2 length: 322456
    # cv2: 962414
    # PIL length: 187792
    # PIL: 637581


bench_pil_vs_cv2()
