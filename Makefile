ENV_FILE = .env

.PHONY: docker_image
docker_image:
	docker build -t time_logger:0.1 -f Dockerfile . --no-cache

.PHONY: env_new
env_new:
	echo "# Docker environment variables" > $(ENV_FILE)
	echo "SANECUM_USERNAME=" >> $(ENV_FILE)
	echo "SANECUM_PASSWORD=" >> $(ENV_FILE)
