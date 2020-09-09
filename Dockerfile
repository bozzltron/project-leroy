# FROM raspbian/stretch
# RUN apt update
# RUN apt install curl gnupg apt-transport-https ca-certificates -y
# # ca-certificates zlib1g-dev libjpeg-dev
# RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
# RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

# RUN apt update
# RUN apt install libedgetpu1-std python3 python3-pip python3-edgetpu python3-opencv ffmpeg   -y
# RUN pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl
# RUN pip3 install image psutil opencv-contrib-python imutils picamera awscli

FROM debian:buster

RUN apt update
RUN apt install curl gnupg ca-certificates zlib1g-dev libjpeg-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libsm6 libxext6 libxrender-dev -y

RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt update
RUN apt install libedgetpu1-std python3 python3-pip python3-edgetpu -y

RUN pip3 install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl

ARG OPENCV_VERSION=4.2.0

# Download OpenCV source
RUN apt install wget cmake clang -y
RUN cd /tmp && \
    wget https://github.com/opencv/opencv/archive/$OPENCV_VERSION.tar.gz && \
    tar -xvzf $OPENCV_VERSION.tar.gz && \
    rm -vrf $OPENCV_VERSION.tar.gz 
    # Configure
RUN mkdir -vp /tmp/opencv-$OPENCV_VERSION/build
WORKDIR /tmp/opencv-$OPENCV_VERSION/build
RUN cmake \
        # Compiler params
        -D CMAKE_BUILD_TYPE=RELEASE \
        -D CMAKE_C_COMPILER=/usr/bin/clang \
        -D CMAKE_CXX_COMPILER=/usr/bin/clang++ \
        -D CMAKE_INSTALL_PREFIX=/usr \
        # No examples
        -D INSTALL_PYTHON_EXAMPLES=NO \
        -D INSTALL_C_EXAMPLES=NO \
        # Support
        -D WITH_IPP=NO \
        -D WITH_1394=NO \
        -D WITH_LIBV4L=NO \
        -D WITH_V4l=YES \
        -D WITH_TBB=YES \
        -D WITH_FFMPEG=YES \
        -D WITH_GPHOTO2=YES \
        -D WITH_GSTREAMER=YES \
        # NO doc test and other bindings
        -D BUILD_DOCS=NO \
        -D BUILD_TESTS=NO \
        -D BUILD_PERF_TESTS=NO \
        -D BUILD_EXAMPLES=NO \
        -D BUILD_opencv_java=NO \
        -D BUILD_opencv_python2=NO \
        -D BUILD_ANDROID_EXAMPLES=NO \
        # Build Python3 bindings only
        -D PYTHON3_LIBRARY=`find /usr -name libpython3.so` \
        -D PYTHON_EXECUTABLE=`which python3` \
        -D PYTHON3_EXECUTABLE=`which python3` \
        -D BUILD_opencv_python3=YES .. 
    # Build
RUN make -j`grep -c '^processor' /proc/cpuinfo`
RUN make install
    # Cleanup
RUN rm -vrf /tmp/opencv-$OPENCV_VERSION

COPY . /usr/src/app
WORKDIR /usr/src/app
RUN pip3 install -r requirements.txt

EXPOSE 5005

ENTRYPOINT ["python3"]
CMD ["leroy.py"]