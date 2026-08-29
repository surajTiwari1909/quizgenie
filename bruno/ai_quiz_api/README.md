# AI Quiz Game Bruno collection

Open this `ai_quiz_api` directory as a collection in Bruno and select the `local`
environment. The collection uses the exact URL paths defined by the Django project.

## Before testing

1. Start PostgreSQL and the Django server on `http://localhost:8000`.
2. Apply migrations with `.venv/bin/python manage.py migrate`.
3. In the `local` environment, replace `documentPath` and `profilePicturePath`
   with absolute paths to a PDF and a JPG, PNG, or WebP image.
4. Configure the project's AI provider before running quiz-generation requests.

## Recommended order

Run requests by folder number. Signup requests can return `400` if the sample users
already exist; in that case run the corresponding Signin request. Successful auth,
upload, quiz, game, and contest requests save tokens and resource IDs into the
selected Bruno environment automatically.

Multiplayer uses two accounts: primary is the host and player is the participant.
Run both signin requests before the Multiplayer folder. Retry requests intentionally
return `409` unless their document or quiz is currently in a failed state. Cleanup
requests delete resources or revoke tokens, so run them last and only when wanted.
