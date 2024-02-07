FROM balenalib/raspberry-pi:bullseye-20210825

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN apt-get update && apt-get install curl -y
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | tee /etc/apt/sources.list.d/coral-cloud.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install make automake gcc g++ subversion python3-dev -y
RUN apt-get install libedgetpu1-std -y
RUN apt-get install python3-pycoral -y
RUN apt-get install python3-opencv -y
RUN apt-get install python3-tflite-runtime -y
RUN apt-get install python3-venv -y
RUN apt-get install python3-pip -y
RUN apt-get clean
#RUN apt-get install python3-edgetpu -y

#COPY requirements.txt ./

RUN python3 -m venv .
RUN pip3 install --upgrade pip setuptools wheel
RUN adduser leroy
USER leroy

RUN python3 -m pip install --user --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
RUN pip3 install --user numpy 
RUN pip3 install --user pillow 
#RUN pip3 install --user opencv-contrib-python 
RUN pip3 install --user psutil 
RUN pip3 install --user imutils 
RUN pip3 install --user picamera

COPY . .

ENTRYPOINT ["python3"]
CMD ["leroy.py"]