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
├── games/                Solo quiz attempts, answers, and scoring
├── profiles/             One-to-one user profile records
├── quizzes/              Quiz, question, and answer-option persistence
├── users/                Function-based authentication views and services
├── manage.py             Django command entry point
├── requirements.txt      Python dependencies
├── Dockerfile             Production container image
├── .dockerignore          Files excluded from the image
├── .github/workflows/     Pull-request checks and image build
├── compose.yaml          Local PostgreSQL, pgAdmin, Redis, and ClamAV containers
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

## Quiz domain

The `quizzes` app persists user-owned quizzes, their ordered questions, and each question's
ordered answer options. A quiz can optionally reference the document it was generated from.
Deleting that source document keeps the quiz and its generated content, while deleting the owner
removes all of their quiz data. Database constraints keep question and answer ordering unique and
allow no more than one correct answer per question.

Authenticated topic-based generation uses these endpoints:

```text
GET  /quizzes                   List the authenticated user's quizzes
POST /quizzes/generate/topic    Queue a topic-based quiz for generation
GET  /quizzes/<id>              Read an owned quiz and its generation state
POST /quizzes/<id>/retry        Retry an owned failed topic quiz
```

Generation runs in the Celery worker and moves a quiz through `generating`, `ready`, or `failed`.
The default provider uses the OpenAI Responses API with schema-constrained output. Set
`OPENAI_API_KEY` and optionally `OPENAI_QUIZ_MODEL` before running the worker. Provider output is
still validated locally: each question must have unique answer text and exactly one correct
option. An invalid question is regenerated independently, leaving valid questions untouched.
`QUIZ_MAX_REGENERATION_ATTEMPTS` controls the per-question retry limit.

Create a five-question quiz:

```bash
curl -X POST http://localhost:8000/quizzes/generate/topic \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Photosynthesis","difficulty":"medium","question_count":5}'
```

## Solo gameplay

Only an owned quiz in the `ready` state can be started. Correct-answer metadata remains hidden
until the attempt is completed.

```text
POST /games/solo                         Start an attempt with a quiz ID
GET  /games/solo/<attempt-id>            Read an owned attempt
POST /games/solo/<attempt-id>/answers    Submit one answer
POST /games/solo/<attempt-id>/complete   Complete and score an attempt
```

Each question can be answered once. Completion requires every question to have an answer; the
response then includes the final score, correct options, and explanations.

## Documents

Authenticated users can upload and manage PDF study material:

```text
GET    /documents       List the authenticated user's documents
POST   /documents       Upload a PDF document
GET    /documents/<id>  Get an owned document
DELETE /documents/<id>  Delete an owned document and its stored file
GET    /documents/<id>/content   Get extracted text when processing is ready
GET    /documents/<id>/download  Securely download an owned document
POST   /documents/<id>/retry     Retry processing for an owned failed document
```

Upload a PDF with a multipart request:

```bash
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer <access-token>" \
  -F "file=@study-notes.pdf"
```

Uploads are limited to PDF files no larger than 10 MB and 250 pages. The byte limit is enforced
while the multipart body is streamed. Each upload is structurally parsed before storage; corrupt,
truncated, encrypted, password-protected, and zero-page PDFs are rejected. The stored content type
is derived from that structural validation rather than trusted multipart metadata. New documents
begin with a `pending` processing status. AI quiz generation is intentionally handled by a later
chunk.

Document extraction runs in a Celery worker. Its status moves through:

```text
pending -> processing -> ready
                      -> failed
```

Successful processing stores extracted text, page count, and character count in a one-to-one
document-content record. Textless or unreadable PDFs become `failed` with a safe failure reason.
Original PDFs are stored under `private_documents/`, outside the public media URL, and can only
be downloaded through the authenticated download endpoint.

Start PostgreSQL, pgAdmin, and Redis, then run the API and worker in separate terminals:

```bash
make db-up
make run
make worker
```

The worker uses `CELERY_BROKER_URL`, which defaults locally to `redis://localhost:6379/0`.

Document uploads also have the following abuse and storage controls:

- SHA-256 duplicate detection per user.
- A default limit of 20 stored documents per user.
- A default total storage limit of 100 MB per user.
- A default authenticated upload rate of 10 requests per hour.
- Fail-closed malware scanning through ClamAV before a file is stored.
- Worker soft/hard processing deadlines and a maximum extracted-character limit.
- A configurable 30-day retention period.

The limits can be changed through the `DOCUMENT_*` environment variables in `.env.example`.
Run `python manage.py purge_expired_documents` from a scheduler to apply the retention policy.
Set `DOCUMENT_RETENTION_DAYS=0` to disable automatic-expiry eligibility. ClamAV may need a short initialization period after
`make db-up` while its signature database becomes ready. Set `CLAMAV_ENABLED=false` only in a
trusted development environment where malware scanning is intentionally unavailable.

## Authentication

The `users` app provides function-based JWT endpoints:

```text
POST /auth/signup          Create a user and an empty profile
POST /auth/signin          Return access and refresh tokens
POST /auth/token/refresh   Get a new access token
POST /auth/logout          Revoke a refresh token
GET  /auth/me              Return the authenticated user
```

Signup expects `username`, `email`, and a password of at least eight characters. Use the returned
access token on protected requests:

```text
Authorization: Bearer <access-token>
```

Access tokens expire after 15 minutes; refresh tokens expire after 7 days.

To log out, send both the access token and the refresh token that should be revoked:

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh-token>"}'
```

A successful logout returns `204 No Content`. The revoked refresh token cannot be used to issue
another access token. The current access token remains valid until its short expiration time.

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

`make db-up` starts PostgreSQL, pgAdmin, Redis, and ClamAV. Open pgAdmin at
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

Authenticated users can upload or replace their profile picture with a multipart request:

```bash
curl -X PUT http://localhost:8000/profiles/me/picture \
  -H "Authorization: Bearer <access-token>" \
  -F "profile_picture=@avatar.png"
```

The response contains an absolute URL for the stored picture:

```json
{
  "profile_picture_url": "http://localhost:8000/media/profiles/12/generated-name.png"
}
```

The endpoint accepts JPG, JPEG, PNG, and WebP images up to 5 MB. Uploading another image
replaces the current picture and removes the former file.

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
make docker-build  # Build the local Docker image
```

## Pull-request checks and Docker image

Every pull request and every push to `main` runs the same checks in GitHub Actions:

1. Install Python dependencies.
2. Run linting, tests, and Django system checks.
3. Build the `quizgenie:ci` Docker image.

The workflow validates the image but does not publish it to a registry. Build and run it locally
with:

```bash
make docker-build
docker run --env-file .env -p 8000:8000 quizgenie:local
```

Stop PostgreSQL, pgAdmin, Redis, and ClamAV without deleting their named volumes:

```bash
make db-down
```
