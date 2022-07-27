FROM raspbian/stretch:latest AS raspbian-stretch-upgrade

ENV DEBIAN_FRONTEND noninteractive

RUN true \
	# Do not start daemons after installation.
	&& echo -e '#!/bin/sh\nexit 101' > /usr/sbin/policy-rc.d \
	&& chmod +x /usr/sbin/policy-rc.d \
	# Update all packages.
	&& apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y \
	# Switch to Bullseye repository.
	&& sed -i 's/stretch/bullseye/g' /etc/apt/sources.list \
	# Update all packages.
	&& apt-get update \
	&& apt-get upgrade -y \
	&& apt-get full-upgrade -y \
	&& apt-get autoremove --purge -y \
	&& apt-get clean -y \
	# Remove files outside base image.
	&& rm -rf /var/lib/apt/lists/* \
	&& rm -f /usr/sbin/policy-rc.d

# Collapse image to single layer.
FROM scratch

COPY --from=raspbian-stretch-upgrade / /

RUN whoami
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN apt-get update && apt-get install curl -y
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | tee /etc/apt/sources.list.d/coral-cloud.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update && apt-get clean
RUN apt-get install libedgetpu1-std -y
RUN apt-get install python3-pycoral -y
RUN apt-get install python3-opencv -y
RUN apt-get install python3-tflite-runtime -y
#RUN apt-get install python3-edgetpu -y

#COPY requirements.txt ./
RUN python3 -m venv .
RUN python3 -m pip install --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
RUN pip3 install numpy pillow opencv-python psutil imutils picamera

COPY . .

ENTRYPOINT ["python3"]
CMD ["leroy.py"]