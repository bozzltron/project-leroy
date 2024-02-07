from python:3.9-slim-bullseye

# Based on:
# OpenCV - https://github.com/mdegans/nano_build_opencv/blob/master/build_opencv.sh
#

# OpenCV Version
ARG OPENCV_VERSION="4.8.0"

# Install build dependencies
RUN apt-get clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
        build-essential binutils \
        ca-certificates cmake cmake-qt-gui curl \
        dbus-x11 \
        ffmpeg \
        gdb gcc g++ gfortran git \
        tar \
        lsb-release \
        procps \
        manpages-dev \
        unzip \
        zip \
        wget \
        xauth \
        swig \
        python3-pip python3-dev python3-numpy python3-distutils \
        python3-setuptools python3-pyqt5 python3-opencv \
        libboost-python-dev libboost-thread-dev libatlas-base-dev libavcodec-dev \
        libavformat-dev libavutil-dev libcanberra-gtk3-module libeigen3-dev \
        libglew-dev libgl1-mesa-dev libgl1-mesa-glx libglib2.0-0 libgtk2.0-dev \
        libgtk-3-dev libjpeg-dev  liblapack-dev \
        #libjpeg8-dev libjpeg-turbo8-dev \
        liblapacke-dev libopenblas-dev libopencv-dev libpng-dev libpostproc-dev \
        libpq-dev libsm6 libswscale-dev libtbb-dev libtbb2 libtesseract-dev \
        libtiff-dev libtiff5-dev libv4l-dev libx11-dev libxext6 libxine2-dev \
        libxrender-dev libxvidcore-dev libx264-dev libgtkglext1 libgtkglext1-dev \
        libvtk9-dev libdc1394-dev libgstreamer-plugins-base1.0-dev \
        libgstreamer1.0-dev libopenexr-dev \
        openexr \
        pkg-config \
        qv4l2 \
        v4l-utils \
        zlib1g-dev \
        locales \
        && locale-gen en_US.UTF-8 \
        && LC_ALL=en_US.UTF-8 \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean

WORKDIR /opencv
RUN wget -O opencv.zip https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip \
    && wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/${OPENCV_VERSION}.zip \
    && unzip opencv.zip \
    && unzip opencv_contrib.zip \
    && mv opencv-${OPENCV_VERSION} opencv \
    && mv opencv_contrib-${OPENCV_VERSION} opencv_contrib

RUN mkdir /opencv/opencv/build
WORKDIR /opencv/opencv/build

RUN cmake -D CMAKE_BUILD_TYPE=RELEASE \
 -D CMAKE_INSTALL_PREFIX=/usr/local \
 -D INSTALL_PYTHON_EXAMPLES=ON \
 -D INSTALL_C_EXAMPLES=ON \
 -D OPENCV_ENABLE_NONFREE=ON \
 -D OPENCV_GENERATE_PKGCONFIG=ON \
 -D OPENCV_EXTRA_MODULES_PATH=/opencv/opencv_contrib/modules \
 -D PYTHON_EXECUTABLE=/usr/local/bin/python \
 -D BUILD_EXAMPLES=ON .. \
    && make -j$(nproc) && make install && ldconfig

RUN apt-get update && apt-get install curl -y
RUN apt-get install make automake gcc g++ subversion python3-dev gnupg2 -y
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN echo "deb https://packages.cloud.google.com/apt coral-cloud-stable main" | tee /etc/apt/sources.list.d/coral-cloud.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN apt-get update
RUN apt-get install libedgetpu1-std -y
RUN apt-get install python3-pycoral -y
RUN apt-get install python3-tflite-runtime -y
RUN apt-get install python3-venv -y
RUN apt-get install python3-pip -y
RUN apt-get install python3-opencv -y
RUN apt-get clean
#RUN apt-get install python3-edgetpu -y

WORKDIR /usr/src/app

RUN python3 -m venv .
RUN pip3 install --upgrade pip setuptools wheel
RUN adduser leroy
USER leroy

RUN python3 -m pip install --user --extra-index-url https://google-coral.github.io/py-repo/ pycoral~=2.0
RUN pip3 install --user numpy 
RUN pip3 install --user pillow 
RUN pip3 install --user opencv-contrib-python 
RUN pip3 install --user psutil 
RUN pip3 install --user imutils 
#RUN pip3 install --user picamera
RUN pip3 install git+https://github.com/waveform80/picamera

COPY . .
ENTRYPOINT ["python3"]
CMD ["leroy.py"]
