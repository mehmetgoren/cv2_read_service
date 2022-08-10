FROM ubuntu:22.04
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update && apt-get upgrade -y
RUN apt-get install -y apt-utils
RUN apt-get install -y curl
RUN apt-get -qq install --no-install-recommends -y python3-pip
RUN apt-get install ffmpeg libsm6 libxext6 -y

RUN pip3 install numpy
RUN pip3 install opencv-python
RUN pip3 install Pillow
RUN pip3 install psutil
RUN pip3 install redis
RUN pip3 install rq

COPY . .

CMD ["python3", "main.py"]
