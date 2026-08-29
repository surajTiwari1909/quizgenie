import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from multiplayer.models import Contest
from quizzes.models import AnswerOption, Question, Quiz

pytestmark = pytest.mark.django_db


def ready_quiz(owner):
    quiz = Quiz.objects.create(owner=owner, title="Science", status=Quiz.Status.READY)
    question = Question.objects.create(quiz=quiz, text="2 + 2?", order=1, points=1)
    correct = AnswerOption.objects.create(question=question, text="4", order=1, is_correct=True)
    incorrect = AnswerOption.objects.create(question=question, text="5", order=2)
    return quiz, question, correct, incorrect


def test_contest_can_be_created_joined_started_answered_and_finished() -> None:
    host = get_user_model().objects.create_user(username="host")
    player = get_user_model().objects.create_user(username="player")
    quiz, question, correct, _incorrect = ready_quiz(host)
    host_client = APIClient()
    host_client.force_authenticate(host)
    player_client = APIClient()
    player_client.force_authenticate(player)

    created = host_client.post(
        reverse("contest-create"), {"quiz_id": quiz.id, "max_players": 5}, format="json"
    )
    code = created.data["code"]
    joined = player_client.post(reverse("contest-join"), {"code": code}, format="json")
    contest_id = created.data["id"]
    started = host_client.post(reverse("contest-start", args=[contest_id]))
    answered = player_client.post(
        reverse("contest-answer", args=[contest_id]),
        {"question_id": question.id, "answer_option_id": correct.id},
        format="json",
    )
    finished = host_client.post(reverse("contest-finish", args=[contest_id]))

    assert created.status_code == 201
    assert created.data["questions"] == []
    assert joined.status_code == 200
    assert joined.data["questions"] == []
    assert started.data["status"] == Contest.Status.ACTIVE
    assert len(started.data["questions"]) == 1
    assert answered.status_code == 200
    assert finished.status_code == 200
    assert finished.data["status"] == Contest.Status.COMPLETED
    assert finished.data["questions"][0]["answer_options"][0].get("is_correct") is None
    player_row = next(row for row in finished.data["participants"] if row["username"] == "player")
    assert player_row["score"] == 1


def test_non_host_cannot_start_or_finish_contest() -> None:
    host = get_user_model().objects.create_user(username="host")
    player = get_user_model().objects.create_user(username="player")
    quiz, _question, _correct, _incorrect = ready_quiz(host)
    host_client = APIClient()
    host_client.force_authenticate(host)
    created = host_client.post(reverse("contest-create"), {"quiz_id": quiz.id}, format="json")
    player_client = APIClient()
    player_client.force_authenticate(player)
    player_client.post(reverse("contest-join"), {"code": created.data["code"]}, format="json")

    assert (
        player_client.post(reverse("contest-start", args=[created.data["id"]])).status_code == 409
    )
    assert (
        player_client.post(reverse("contest-finish", args=[created.data["id"]])).status_code == 409
    )
