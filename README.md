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
├── profiles/             One-to-one user profile records
├── users/                Function-based authentication views and services
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

## Authentication

The `users` app provides function-based JWT endpoints:

```text
POST /auth/signup          Create a user and an empty profile
POST /auth/signin          Return access and refresh tokens
POST /auth/token/refresh   Get a new access token
GET  /auth/me              Return the authenticated user
```

Signup expects `username`, `email`, and a password of at least eight characters. Use the returned
access token on protected requests:

```text
Authorization: Bearer <access-token>
```

Access tokens expire after 15 minutes; refresh tokens expire after 7 days.

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

## Media storage

Profile pictures are optional and are stored locally during development under:

```text
media/profiles/<user-id>/<generated-file-name>
```

The database stores only the relative file path. Uploaded profile pictures are limited to 5 MB
and the supported extensions are JPG, JPEG, PNG, and WebP. The `media/` directory is ignored by
Git. Production media should later use external object storage instead of the application disk.

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
