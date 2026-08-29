from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from quizzes import services
from quizzes.models import Quiz
from quizzes.providers import OpenAIQuestionGenerator
from quizzes.validation import GeneratedAnswerOption, GeneratedQuestion

pytestmark = pytest.mark.django_db


def valid_question(text: str = "What is 2 + 2?") -> GeneratedQuestion:
    return GeneratedQuestion(
        text=text,
        explanation="Two and two make four.",
        options=(
            GeneratedAnswerOption(text="4", is_correct=True),
            GeneratedAnswerOption(text="5", is_correct=False),
        ),
    )


def invalid_question() -> GeneratedQuestion:
    return GeneratedQuestion(
        text="",
        explanation="",
        options=(
            GeneratedAnswerOption(text="Same", is_correct=True),
            GeneratedAnswerOption(text="same", is_correct=True),
        ),
    )


class RegeneratingGenerator:
    def __init__(self, replacement: GeneratedQuestion | None = None) -> None:
        self.replacement = replacement or valid_question("Replacement question")
        self.regeneration_calls: list[GeneratedQuestion | None] = []

    def generate_questions(self, **_kwargs) -> list[GeneratedQuestion]:
        return [valid_question("Accepted question"), invalid_question()]

    def regenerate_question(self, *, question, **_kwargs) -> GeneratedQuestion:
        self.regeneration_calls.append(question)
        return self.replacement


def test_invalid_question_is_regenerated_without_replacing_valid_question() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz = Quiz.objects.create(
        owner=user,
        title="Math",
        topic="Arithmetic",
        requested_question_count=2,
        status=Quiz.Status.GENERATING,
    )
    generator = RegeneratingGenerator()

    services.process_topic_quiz(quiz.id, generator=generator)

    quiz.refresh_from_db()
    questions = list(quiz.questions.all())
    assert quiz.status == Quiz.Status.READY
    assert [question.text for question in questions] == [
        "Accepted question",
        "Replacement question",
    ]
    assert [question.generation_attempts for question in questions] == [1, 2]
    assert len(generator.regeneration_calls) == 1
    assert generator.regeneration_calls[0] == invalid_question()


def test_generation_failure_is_safe_after_independent_retries(settings) -> None:
    settings.QUIZ_MAX_REGENERATION_ATTEMPTS = 2
    user = get_user_model().objects.create_user(username="learner")
    quiz = Quiz.objects.create(
        owner=user,
        title="Math",
        topic="Arithmetic",
        requested_question_count=2,
        status=Quiz.Status.GENERATING,
    )
    generator = RegeneratingGenerator(replacement=invalid_question())

    services.process_topic_quiz(quiz.id, generator=generator)

    quiz.refresh_from_db()
    assert quiz.status == Quiz.Status.FAILED
    assert quiz.questions.count() == 0
    assert quiz.failure_reason == "Question 2 remained invalid after regeneration."
    assert len(generator.regeneration_calls) == 2


def test_topic_generation_endpoint_creates_owned_generating_quiz(
    django_capture_on_commit_callbacks,
) -> None:
    user = get_user_model().objects.create_user(username="learner")
    client = APIClient()
    client.force_authenticate(user)

    with (
        patch("quizzes.services.enqueue_quiz_generation") as enqueue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = client.post(
            reverse("quiz-generate-topic"),
            {
                "topic": "Photosynthesis",
                "difficulty": "hard",
                "question_count": 3,
            },
            format="json",
        )

    assert response.status_code == 202
    quiz = Quiz.objects.get(id=response.data["id"])
    assert quiz.owner == user
    assert quiz.title == "Photosynthesis"
    assert quiz.status == Quiz.Status.GENERATING
    assert quiz.requested_question_count == 3
    enqueue.assert_called_once_with(quiz.id)


def test_users_cannot_read_another_users_quiz() -> None:
    owner = get_user_model().objects.create_user(username="owner")
    other_user = get_user_model().objects.create_user(username="other")
    quiz = Quiz.objects.create(owner=owner, title="Private")
    client = APIClient()
    client.force_authenticate(other_user)

    response = client.get(reverse("quiz-detail", args=[quiz.id]))

    assert response.status_code == 404


def test_openai_provider_requests_strict_structured_output(settings) -> None:
    settings.OPENAI_API_KEY = "test-key"
    settings.OPENAI_QUIZ_MODEL = "test-model"
    response = SimpleNamespace(
        output_text=(
            '{"questions":[{"text":"Question","explanation":"Explanation",'
            '"points":1,"options":[{"text":"Correct","is_correct":true},'
            '{"text":"Incorrect","is_correct":false}]}]}'
        )
    )

    with patch("openai.OpenAI") as client_class:
        client_class.return_value.responses.create.return_value = response
        questions = OpenAIQuestionGenerator().generate_questions(
            topic="Testing",
            difficulty="medium",
            question_count=1,
        )

    assert questions == [
        GeneratedQuestion(
            text="Question",
            explanation="Explanation",
            points=1,
            options=(
                GeneratedAnswerOption(text="Correct", is_correct=True),
                GeneratedAnswerOption(text="Incorrect", is_correct=False),
            ),
        )
    ]
    call = client_class.return_value.responses.create.call_args.kwargs
    assert call["model"] == "test-model"
    assert call["store"] is False
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
