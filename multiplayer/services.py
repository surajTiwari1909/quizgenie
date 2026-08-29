import secrets
import string
from typing import Any

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from multiplayer.models import Contest, ContestAnswer, ContestParticipant
from quizzes.models import AnswerOption, Question, Quiz


class ContestStateError(Exception):
    """The contest cannot perform the requested transition."""


class ContestAnswerError(Exception):
    """The submitted contest answer is invalid."""


def create_contest(*, host: Any, quiz: Quiz, max_players: int) -> Contest:
    if quiz.status != Quiz.Status.READY or not quiz.questions.exists():
        raise ContestStateError("Only ready quizzes with questions can host a contest.")
    for _ in range(5):
        code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        try:
            with transaction.atomic():
                contest = Contest.objects.create(
                    host=host, quiz=quiz, code=code, max_players=max_players
                )
                ContestParticipant.objects.create(contest=contest, user=host)
            return contest
        except Exception as error:
            if "unique" not in str(error).lower():
                raise
    raise ContestStateError("Could not create a unique contest code.")


def join_contest(*, user: Any, code: str) -> ContestParticipant:
    with transaction.atomic():
        contest = Contest.objects.select_for_update().get(code=code.upper())
        if contest.status != Contest.Status.WAITING:
            raise ContestStateError("This contest is no longer accepting players.")
        participant, created = ContestParticipant.objects.get_or_create(contest=contest, user=user)
        if not created:
            return participant
        if contest.participants.count() > contest.max_players:
            participant.delete()
            raise ContestStateError("This contest is full.")
        return participant


def start_contest(*, contest: Contest, user: Any) -> Contest:
    if contest.host_id != user.id:
        raise ContestStateError("Only the contest host can start it.")
    with transaction.atomic():
        locked = Contest.objects.select_for_update().get(pk=contest.pk)
        if locked.status != Contest.Status.WAITING:
            raise ContestStateError("Only a waiting contest can be started.")
        locked.status = Contest.Status.ACTIVE
        locked.started_at = timezone.now()
        locked.save(update_fields=["status", "started_at"])
        return locked


def submit_contest_answer(
    *, participant: ContestParticipant, question_id: int, selected_option_id: int
) -> ContestAnswer:
    with transaction.atomic():
        locked = (
            ContestParticipant.objects.select_for_update()
            .select_related("contest")
            .get(pk=participant.pk)
        )
        if locked.contest.status != Contest.Status.ACTIVE:
            raise ContestStateError("Answers can only be submitted while the contest is active.")
        try:
            question = Question.objects.get(id=question_id, quiz=locked.contest.quiz)
            option = AnswerOption.objects.get(id=selected_option_id, question=question)
        except (Question.DoesNotExist, AnswerOption.DoesNotExist) as error:
            raise ContestAnswerError(
                "The question or option does not belong to this contest."
            ) from error
        if ContestAnswer.objects.filter(participant=locked, question=question).exists():
            raise ContestStateError("This question has already been answered.")
        answer = ContestAnswer.objects.create(
            participant=locked,
            question=question,
            selected_option=option,
            is_correct=option.is_correct,
            awarded_points=question.points if option.is_correct else 0,
        )
        locked.score = locked.answers.aggregate(total=Sum("awarded_points"))["total"] or 0
        locked.save(update_fields=["score"])
        return answer


def finish_contest(*, contest: Contest, user: Any) -> Contest:
    if contest.host_id != user.id:
        raise ContestStateError("Only the contest host can finish it.")
    with transaction.atomic():
        locked = Contest.objects.select_for_update().get(pk=contest.pk)
        if locked.status == Contest.Status.COMPLETED:
            return locked
        if locked.status != Contest.Status.ACTIVE:
            raise ContestStateError("Only an active contest can be finished.")
        locked.status = Contest.Status.COMPLETED
        locked.completed_at = timezone.now()
        locked.save(update_fields=["status", "completed_at"])
        return locked


def contest_snapshot(contest: Contest) -> dict:
    participants = list(
        contest.participants.select_related("user").annotate(answer_count=Count("answers"))
    )
    return {
        "participants": [
            {
                "user_id": participant.user_id,
                "username": participant.user.get_username(),
                "score": participant.score,
                "answered_count": participant.answer_count,
            }
            for participant in participants
        ]
    }
