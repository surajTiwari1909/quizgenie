# QuizGenie

Django backend foundation for the AI-powered quiz game. The current scope contains only
application startup, environment configuration, PostgreSQL access, health endpoints, Django
migrations, and tests. Quiz generation and gameplay apps will be added one approved chunk at a
time.

## Project structure

```text
AI_project/
├── config/               Django project settings and main URL routing
├── core/                 Shared health endpoints and common foundations
│   ├── migrations/       Database migrations owned by the core app
│   └── tests/            Tests owned by the core app
├── manage.py             Django command entry point
├── requirements.txt      Python dependencies
├── compose.yaml          Local PostgreSQL and pgAdmin containers
├── docker/pgadmin/       Preconfigured pgAdmin server connection
├── Makefile              Short development commands
└── .env.example          Environment-variable example
```

This follows the normal Django layout. Future chunks can add clear root-level apps such as:

```text
users/                    User accounts and permissions
quizzes/                  Quiz configuration and questions
documents/                Study-material uploads and analysis
games/                    Solo gameplay and attempts
multiplayer/              Live contests
```

Each app will own its models, migrations, API views, services, and tests. We will create an app
only when its implementation chunk is selected.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
make db-up
make migrate
make run
```

## PostgreSQL and pgAdmin

`make db-up` starts both PostgreSQL and pgAdmin. Open pgAdmin at
`http://localhost:5050` and sign in with the development defaults:

```text
Email:    admin@quiz.local
Password: admin_password
```

The `AI Quiz PostgreSQL` server is registered automatically. When pgAdmin asks for the database
password, use `quiz_password`. These values come from `.env` and should be changed outside local
development.

The API listens on `http://localhost:8000` by default:

- `GET /health` checks that the API process is running.
- `GET /ready` checks PostgreSQL connectivity.

Run verification with:

```bash
make check
```

Useful commands:

```bash
make migrations    # Create migrations after a model change
make migrate       # Apply migrations
make test          # Run tests
make lint          # Run the linter
```

Stop PostgreSQL and pgAdmin without deleting their named volumes:

```bash
make db-down
```
