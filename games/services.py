from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from games.models import SoloAnswer, SoloAttempt
from quizzes.models import AnswerOption, Question, Quiz


class InvalidAttemptState(Exception):
    """The requested operation is invalid for this solo attempt."""


class InvalidQuizForGameplay(Exception):
    """The quiz cannot currently be played."""


class InvalidAnswer(Exception):
    """The submitted question or option does not belong to the attempt."""


def start_solo_attempt(*, user: Any, quiz: Quiz) -> SoloAttempt:
    if quiz.status != Quiz.Status.READY:
        raise InvalidQuizForGameplay("Only ready quizzes can be played.")

    questions = list(quiz.questions.prefetch_related("answer_options").all())
    if not questions:
        raise InvalidQuizForGameplay("The quiz has no questions.")
    for question in questions:
        if sum(option.is_correct for option in question.answer_options.all()) != 1:
            raise InvalidQuizForGameplay(
                f"Question {question.order} does not have exactly one correct answer."
            )

    return SoloAttempt.objects.create(
        user=user,
        quiz=quiz,
        max_score=sum(question.points for question in questions),
        question_count=len(questions),
        expires_at=timezone.now() + timedelta(seconds=settings.SOLO_ATTEMPT_TIME_LIMIT_SECONDS),
    )


def submit_solo_answer(
    *,
    attempt: SoloAttempt,
    question_id: int,
    selected_option_id: int,
) -> SoloAnswer:
    with transaction.atomic():
        locked_attempt = SoloAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.status != SoloAttempt.Status.IN_PROGRESS:
            raise InvalidAttemptState("This attempt has already been completed.")
        if locked_attempt.expires_at and locked_attempt.expires_at <= timezone.now():
            _expire_attempt(locked_attempt)
            raise InvalidAttemptState("This attempt has expired.")

        try:
            question = Question.objects.get(id=question_id, quiz=locked_attempt.quiz)
            selected_option = AnswerOption.objects.get(
                id=selected_option_id,
                question=question,
            )
        except (Question.DoesNotExist, AnswerOption.DoesNotExist) as error:
            raise InvalidAnswer(
                "The selected question or answer option does not belong to this quiz."
            ) from error

        if SoloAnswer.objects.filter(attempt=locked_attempt, question=question).exists():
            raise InvalidAttemptState("This question has already been answered.")

        is_correct = selected_option.is_correct
        answer = SoloAnswer.objects.create(
            attempt=locked_attempt,
            question=question,
            selected_option=selected_option,
            is_correct=is_correct,
            awarded_points=question.points if is_correct else 0,
        )
        locked_attempt.score = (
            locked_attempt.answers.aggregate(total=Sum("awarded_points"))["total"] or 0
        )
        locked_attempt.save(update_fields=["score"])
        return answer


def complete_solo_attempt(attempt: SoloAttempt) -> SoloAttempt:
    with transaction.atomic():
        locked_attempt = SoloAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked_attempt.status == SoloAttempt.Status.COMPLETED:
            return locked_attempt

        if locked_attempt.expires_at and locked_attempt.expires_at <= timezone.now():
            _expire_attempt(locked_attempt)
            return locked_attempt

        answered_count = locked_attempt.answers.aggregate(count=Count("id"))["count"]
        if answered_count != locked_attempt.question_count:
            raise InvalidAttemptState("Every question must be answered before completion.")

        locked_attempt.score = (
            locked_attempt.answers.aggregate(total=Sum("awarded_points"))["total"] or 0
        )
        locked_attempt.status = SoloAttempt.Status.COMPLETED
        locked_attempt.completed_at = timezone.now()
        locked_attempt.save(update_fields=["score", "status", "completed_at"])
        return locked_attempt


def _expire_attempt(attempt: SoloAttempt) -> None:
    attempt.status = SoloAttempt.Status.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["status", "completed_at"])


def list_solo_attempts(*, user: Any):
    return SoloAttempt.objects.filter(user=user).select_related("quiz")
