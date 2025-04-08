# Default to Docker, allow override with DOCKER_TOOL=podman
DOCKER_TOOL ?= docker
COMPOSE_FILE = docker-compose.yml
SERVICE_NAME = wbor-archiver
PROJECT_NAME = wbor-archiver
COMPOSE_BAKE = true

default: up

build:
	@echo "Building images..."
	COMPOSE_BAKE=$(COMPOSE_BAKE) $(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) build

up: build
	@echo "Starting containers..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) up -d

down:
	@echo "Stopping and removing containers..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down

logs:
	@echo "Tailing logs for $(SERVICE_NAME)..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) logs -f

restart: down up

watch:
	@echo "Watching for file changes and restarting containers..."
	while inotifywait -r -e modify,create,delete ./; do \
		$(MAKE) restart; \
	done

clean:
	@echo "Cleaning up containers, networks, volumes, and images..."
	$(DOCKER_TOOL) compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE) down -v --rmi all
