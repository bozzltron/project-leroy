IMAGE=project-leroy

recent_logs:
	journalctl -u leroy.service -b

logs:
	journalctl -u leroy.service

status:
	sudo systemctl status leroy.service

start:
	sudo systemctl start leroy.service

stop:
	sudo systemctl status leroy.service

classify:
  python3 classify.py --dir=storage/detected

sync_from_pi:
	rsync -r -a -v -e "ssh -p22" --delete pi@10.0.4.79:/home/pi/Projects/project-leroy/storage `pwd`/storage/ 