import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from games.models import SoloAttempt
from quizzes.models import AnswerOption, Question, Quiz

pytestmark = pytest.mark.django_db


def create_ready_quiz(owner) -> tuple[Quiz, list[Question], list[list[AnswerOption]]]:
    quiz = Quiz.objects.create(owner=owner, title="Math", status=Quiz.Status.READY)
    questions: list[Question] = []
    options: list[list[AnswerOption]] = []
    for order in (1, 2):
        question = Question.objects.create(
            quiz=quiz,
            text=f"Question {order}",
            order=order,
            points=order,
            explanation=f"Explanation {order}",
        )
        question_options = [
            AnswerOption.objects.create(
                question=question,
                text="Correct",
                is_correct=True,
                order=1,
            ),
            AnswerOption.objects.create(
                question=question,
                text="Incorrect",
                order=2,
            ),
        ]
        questions.append(question)
        options.append(question_options)
    return quiz, questions, options


def test_solo_attempt_scores_answers_and_reveals_results_only_on_completion() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz, questions, options = create_ready_quiz(user)
    client = APIClient()
    client.force_authenticate(user)

    start = client.post(reverse("solo-attempt-start"), {"quiz_id": quiz.id}, format="json")

    assert start.status_code == 201
    assert start.data["max_score"] == 3
    assert start.data["answers"] == []
    assert "is_correct" not in start.data["questions"][0]["answer_options"][0]
    attempt_id = start.data["id"]

    first_answer = client.post(
        reverse("solo-answer-submit", args=[attempt_id]),
        {"question_id": questions[0].id, "answer_option_id": options[0][0].id},
        format="json",
    )
    second_answer = client.post(
        reverse("solo-answer-submit", args=[attempt_id]),
        {"question_id": questions[1].id, "answer_option_id": options[1][1].id},
        format="json",
    )
    completed = client.post(reverse("solo-attempt-complete", args=[attempt_id]))

    assert first_answer.status_code == 200
    assert first_answer.data["answers"] == []
    assert second_answer.status_code == 200
    assert completed.status_code == 200
    assert completed.data["status"] == SoloAttempt.Status.COMPLETED
    assert completed.data["score"] == 1
    assert completed.data["max_score"] == 3
    assert [answer["is_correct"] for answer in completed.data["answers"]] == [True, False]
    assert completed.data["answers"][0]["correct_option_id"] == options[0][0].id


def test_attempt_cannot_complete_before_every_question_is_answered() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz, _questions, _options = create_ready_quiz(user)
    client = APIClient()
    client.force_authenticate(user)
    start = client.post(reverse("solo-attempt-start"), {"quiz_id": quiz.id}, format="json")

    response = client.post(reverse("solo-attempt-complete", args=[start.data["id"]]))

    assert response.status_code == 409
    assert "Every question" in response.data["detail"]


def test_question_cannot_be_answered_twice() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz, questions, options = create_ready_quiz(user)
    client = APIClient()
    client.force_authenticate(user)
    start = client.post(reverse("solo-attempt-start"), {"quiz_id": quiz.id}, format="json")
    payload = {"question_id": questions[0].id, "answer_option_id": options[0][0].id}
    client.post(reverse("solo-answer-submit", args=[start.data["id"]]), payload, format="json")

    response = client.post(
        reverse("solo-answer-submit", args=[start.data["id"]]),
        payload,
        format="json",
    )

    assert response.status_code == 409
    assert "already been answered" in response.data["detail"]


def test_user_cannot_access_another_users_attempt() -> None:
    owner = get_user_model().objects.create_user(username="owner")
    other_user = get_user_model().objects.create_user(username="other")
    quiz, _questions, _options = create_ready_quiz(owner)
    attempt = SoloAttempt.objects.create(
        user=owner,
        quiz=quiz,
        max_score=3,
        question_count=2,
    )
    client = APIClient()
    client.force_authenticate(other_user)

    response = client.get(reverse("solo-attempt-detail", args=[attempt.id]))

    assert response.status_code == 404

