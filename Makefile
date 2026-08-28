.PHONY: install run db-up db-down migrate migrations test lint check

install:
	.venv/bin/python -m pip install -r requirements.txt

run:
	.venv/bin/python manage.py runserver 0.0.0.0:8000

db-up:
	docker compose up -d postgres pgadmin

db-down:
	docker compose down

migrate:
	.venv/bin/python manage.py migrate

migrations:
	.venv/bin/python manage.py makemigrations

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

check: lint test
	.venv/bin/python manage.py check
