.PHONY: install run worker db-up db-down migrate migrations test lint check docker-build

install:
	python -m pip install -r requirements.txt

run:
	python manage.py runserver 0.0.0.0:8000

worker:
	celery -A config worker --loglevel=INFO

db-up:
	docker compose up -d postgres pgadmin redis clamav

db-down:
	docker compose down

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations

test:
	python -m pytest

lint:
	python -m ruff check .

check: lint test
	python manage.py check

docker-build:
	docker build -t quizgenie:local .
