ENV_FILE = .env

code_prepare:
	isort .
	black .
	flake8 .

.PHONY: docker_image
docker_image:
	docker build -t time_logger:0.1 -f Dockerfile . --no-cache

.PHONY: env_new
env_new:
	echo "# Docker environment variables" > $(ENV_FILE)
	echo "SANECUM_USERNAME=" >> $(ENV_FILE)
	echo "SANECUM_PASSWORD=" >> $(ENV_FILE)
	echo "REDMINE_USERNAME=" >> $(ENV_FILE)
	echo "REDMINE_PASSWORD=" >> $(ENV_FILE)

.PHONY: ars_sanecum
ars_sanecum:
	docker compose run --rm logger --format py --platform kimai --src "data.sanecum.log_days" --show_only
	docker compose run --rm logger --format py --platform redmine --src "data.sanecum.log_days" --show_only

.PHONY: ars_bg
ars_bg:
	docker compose run --rm logger --format py --platform redmine --src "data.body_gen.log_days" --show_task

.PHONY: ars_hanebutt
ars_hanebutt:
	docker compose run --rm logger --format py --platform redmine --src "data.hanebutt.log_days" --show_only
