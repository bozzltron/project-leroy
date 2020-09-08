FROM raspbian/stretch
RUN apt update
RUN apt install curl gnupg apt-transport-https ca-certificates -y
# ca-certificates zlib1g-dev libjpeg-dev
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt update
RUN apt install libedgetpu1-std python3 python3-pip python3-edgetpu python3-opencv ffmpeg gstreamer1.0-tools libxvidcore-dev libx264-dev libgstreamer1.0- libgstreamer-plugins-base1.0- gstreamer1.0-plugins-*  -y
RUN pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl
RUN pip3 install image psutil opencv-contrib-python imutils picamera awscli

COPY . /usr/src/app
WORKDIR /usr/src/app
ENTRYPOINT python3 leroy.py