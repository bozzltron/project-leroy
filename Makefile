IMAGE=project-leroy

build:
	docker build . -t $(IMAGE):latest

run: build
	docker run -t $(IMAGE):latest

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
	rsync -r -a -v -e "ssh -p22" --delete pi@10.0.4.79:/home/pi/Projects/project-leroy/storage `pwd`/storage/ 

copy_from_pi:
	scp -r pi@10.0.4.79:/home/pi/Projects/project-leroy/storage/classified/ `pwd`/storage/classified/