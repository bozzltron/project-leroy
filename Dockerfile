FROM python:3.7-bullseye

WORKDIR /usr/src/app

RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | tee /etc/apt/sources.list.d/coral-cloud.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install libedgetpu1-std -y
RUN apt-get install python3-pycoral -y
RUN apt-get install python3-opencv -y
RUN apt-get install python3-tflite-runtime -y
#RUN apt-get install python3-edgetpu -y

#COPY requirements.txt ./
RUN python3 -m venv .
RUN pip3 install numpy pillow
RUN python3 -m pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0

COPY . .


ENTRYPOINT ["python3"]
CMD ["leroy.py"]