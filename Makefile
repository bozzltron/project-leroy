# Makefile for Project Leroy
# Raspberry Pi 5 + AI Kit (Hailo) implementation

.PHONY: help service_* docker-pi5-* nginx-* web-preview tail cron_logs

help:
	@echo "Project Leroy - Makefile Commands"
	@echo ""
	@echo "Service Management:"
	@echo "  make service_status      - Check service status"
	@echo "  make service_start       - Start service"
	@echo "  make service_stop        - Stop service"
	@echo "  make service_restart     - Restart service"
	@echo "  make service_logs        - View service logs"
	@echo "  make service_recent_logs - View recent logs (this boot)"
	@echo ""
	@echo "Testing (Docker):"
	@echo "  make docker-pi5-test     - Run all tests"
	@echo "  make docker-pi5-test-file TEST=... - Run specific test"
	@echo ""
	@echo "Linting (Docker):"
	@echo "  make docker-pi5-lint     - Run linter on Python files"
	@echo ""
	@echo "Web Preview (Local Dev):"
	@echo "  make web-preview         - Preview web app locally"
	@echo ""
	@echo "Utilities:"
	@echo "  make tail                - Tail results.log"
	@echo "  make cron_logs           - View cron logs"

# Service management (systemd)
service_status:
	sudo systemctl status leroy.service

service_start:
	sudo systemctl start leroy.service

service_stop:
	sudo systemctl stop leroy.service

service_restart:
	sudo systemctl restart leroy.service

service_logs:
	sudo journalctl -u leroy.service -f

service_recent_logs:
	sudo journalctl -u leroy.service -b

# Docker commands for Pi 5 testing (local development)
docker-pi5-build:
	docker build -f Dockerfile.pi5 -t project-leroy-pi5 .

docker-pi5-test:
	docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
		"cd /app && source venv/bin/activate && python3 -m unittest discover tests -v"

docker-pi5-test-file:
	docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
		"cd /app && source venv/bin/activate && python3 -m unittest $(TEST) -v"

docker-pi5-lint:
	docker-compose -f docker-compose.pi5.yml run --rm leroy-pi5 bash -c \
		"cd /app && source venv/bin/activate && python3 -m flake8 --exclude=venv,storage,all_models --max-line-length=120 --ignore=E501,W503 *.py || python3 -m py_compile *.py 2>&1 | head -20"

# Web preview (local development only)
web-preview:
	@echo "Starting nginx for web preview..."
	@echo "Open http://localhost:8080 in your browser"
	docker-compose -f docker-compose.nginx.yml up

# Utilities
tail:
	tail -f storage/results.log

cron_logs:
	grep CRON /var/log/syslog
