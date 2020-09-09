IMAGE=michaelbosworth/project-leroy

build:
	docker build . -t $(IMAGE):latest

push:
	docker push $(IMAGE):latest

run:
	docker run -t --privileged --device /dev/video0  --restart unless-stopped --device /dev/gpiomem -v `pwd`/storage:/usr/src/app/storage -p 5005:5005 -v /dev/bus/usb:/dev/bus/usb -t $(IMAGE):latest

start_machine:
	docker-machine start

change_docker_env: start_machine
	eval $(docker-machine env default)

run_on_mac:
	docker run -it --privileged --device /dev/video0 -v `pwd`:/usr/app/src -v /dev/bus/usb:/dev/bus/usb -v `pwd`/dev_storage:/usr/src/app/storage -p 5005:5005 -t $(IMAGE):latest

restore_docker_env:
	docker-machine stop
	eval $(docker-machine env -u)

recent_logs:
	sudo journalctl -u leroy.service -b

logs:
	sudo journalctl -u leroy.service

status:
	sudo systemctl status leroy.service

start:
	sudo systemctl start leroy.service

stop:
	sudo systemctl status leroy.service

pi_edit_service:
	sudo nano /etc/systemd/system/leroy.service

classify:
  python3 classify.py --dir=storage/detected

sync_from_pi:
	rsync --remove-source-files --exclude 'detected/*' --exclude 'results.log' -avzhe "ssh -p22" pi@10.0.4.79:/home/pi/Projects/project-leroy/storage/ `pwd`/storage

sync_to_pi:
	rsync --remove-source-files -avzhe "ssh -p22" `pwd`/storage/detected/ pi@10.0.4.79:/home/pi/Projects/project-leroy/storage/detected

mp4_to_gif:
	docker run -t -e INPUT=${INPUT} -e OUTPUT=${OUTPUT} -v `pwd`/storage/:/usr/src/app/ --entrypoint="ffmpeg" $(IMAGE):latest  \
		-i ${INPUT} -ss 1 -t 5 -vf "fps=4,scale=1024:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" ${OUTPUT} 

mp4_to_h264:
	docker run -t -e INPUT=${INPUT} -e OUTPUT=${OUTPUT} -v `pwd`:/usr/src/app/ --entrypoint="sh" $(IMAGE):latest ./encode.sh 
	
bash:
	docker run -it -v `pwd`/storage/:/usr/src/app/ --entrypoint="bash" $(IMAGE):latest