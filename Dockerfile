FROM python:3.7-bullseye

WORKDIR /usr/src/app
ENV READTHEDOCS=True

RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | tee /etc/apt/sources.list.d/coral-cloud.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install libedgetpu1-std python3-pycoral python3-opencv python3-tflite-runtime -y
#RUN apt-get install python3-edgetpu -y

#COPY requirements.txt ./
RUN python3 -m venv .
RUN python3 -m pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
RUN pip3 install numpy pillow opencv-python psutil imutils picamera

COPY . .


ENTRYPOINT ["python3"]
CMD ["leroy.py"]