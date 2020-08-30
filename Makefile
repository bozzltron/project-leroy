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
