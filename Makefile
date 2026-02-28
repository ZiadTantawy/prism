# Prism - Development commands

.PHONY: up down migrate revision upgrade downgrade

# Docker Compose
up:
	docker compose up -d

down:
	docker compose down

# Alembic migrations (run from project root with venv activated)
ALEMBIC_CFG = src/database/migrations/alembic.ini

migrate:
	PYTHONPATH=. alembic -c $(ALEMBIC_CFG) upgrade head

revision:
	PYTHONPATH=. alembic -c $(ALEMBIC_CFG) revision --autogenerate -m "$(or $(msg),model changes)"

upgrade:
	PYTHONPATH=. alembic -c $(ALEMBIC_CFG) upgrade head

downgrade:
	PYTHONPATH=. alembic -c $(ALEMBIC_CFG) downgrade -1
