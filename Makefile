IMAGE=michaelbosworth/project-leroy

build:
	docker build . -t $(IMAGE):latest

build_alpine:
	docker build . -f alpine.Dockerfile -t $(IMAGE):alpine

push:
	docker push $(IMAGE):latest

run:
	docker run -t --privileged --device /dev/video0  --restart unless-stopped --device /dev/gpiomem -v `pwd`/storage:/usr/src/app/storage -v /dev/bus/usb:/dev/bus/usb -t $(IMAGE):latest

run_experiment:
	docker run -t --privileged --device /dev/video0  --restart unless-stopped --device /dev/gpiomem -v `pwd`/storage:/usr/src/app/storage -v /dev/bus/usb:/dev/bus/usb -t jjanzic/docker-python3-opencv:contrib-opencv-4.0.1 python3 leroy.py	

start_machine:
	docker-machine start

change_docker_env: start_machine
	eval $(docker-machine env default)

run_on_mac:
	docker run -it --privileged --device /dev/video0 -v `pwd`:/usr/app/src -v /dev/bus/usb:/dev/bus/usb -v `pwd`/dev_storage:/usr/src/app/storage -p 5005:5005 -t $(IMAGE):latest

restore_docker_env:
	docker-machine stop
	eval $(docker-machine env -u)

service_recent_logs:
	sudo journalctl -u leroy.service -b

service_logs:
	sudo journalctl -u leroy.service

service_status:
	sudo systemctl status leroy.service

service_start:
	sudo systemctl start leroy.service

service_stop:
	sudo systemctl stop leroy.service

service_edit:
	sudo nano /lib/systemd/system/leroy.service

service_reload:
	sudo systemctl daemon-reload

service_enable:
	sudo systemctl enable leroy.service

service_disable:
	sudo systemctl disable leroy.service

service_restart:
	sudo systemctl restart leroy.service

cron_logs:
	grep CRON /var/log/syslog

pi_edit_service:
	sudo nano /etc/systemd/system/leroy.service

classify:
	docker run -t -e DRY_RUN=${DRY_RUN} -v `pwd`:/usr/src/app/ $(IMAGE):latest classify.py --dir=storage/detected --dryrun=${DRY_RUN}

generate_daily_report:
	docker run -t -e DATE=${DATE} -v /var/www/html:/var/www/html -v `pwd`:/usr/src/app/ $(IMAGE):latest visitation.py --dir=/var/www/html/classified --date=${DATE}

sync_from_pi:
	rsync --remove-source-files --exclude 'detected/*' --exclude 'results.log' -avzhe "ssh -p22" pi@10.0.4.79:/var/www/html/classified/ `pwd`/storage/classifed

sync_to_pi:
	rsync --remove-source-files -avzhe "ssh -p22" `pwd`/storage/detected/ pi@10.0.4.79:/home/pi/Projects/project-leroy/storage/detected

mp4_to_gif:
	docker run -t -e INPUT=${INPUT} -e OUTPUT=${OUTPUT} -v `pwd`/storage/:/usr/src/app/ --entrypoint="ffmpeg" $(IMAGE):latest  \
		-i ${INPUT} -ss 1 -t 5 -vf "fps=4,scale=1024:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" ${OUTPUT} 

mp4_to_h264:
	docker run -t -e INPUT=${INPUT} -e OUTPUT=${OUTPUT} -v `pwd`:/usr/src/app/ --entrypoint="sh" $(IMAGE):latest ./encode.sh 

bash:
	docker run -it -v `pwd`/storage/:/usr/src/app/ --entrypoint="bash" $(IMAGE):latest

set_resolution:
	v4l2-ctl -v width=3280,height=2464	
	bcm2835-v4l2 max_video_width=3280 max_video_height=2464

tail:
	tail -f storage/results.log