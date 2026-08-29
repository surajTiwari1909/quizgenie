from django.conf import settings
from django.db import models
from django.db.models import Q

from quizzes.models import AnswerOption, Question, Quiz


class Contest(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_contests",
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="contests")
    code = models.CharField(max_length=12, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.WAITING)
    max_players = models.PositiveSmallIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(max_players__gte=2) & Q(max_players__lte=100),
                name="contest_player_limit_range",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.quiz.title}"


class ContestParticipant(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contest_participations",
    )
    score = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-score", "joined_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("contest", "user"),
                name="one_contest_participation_per_user",
            )
        ]


class ContestAnswer(models.Model):
    participant = models.ForeignKey(
        ContestParticipant,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="contest_answers")
    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contest_selections",
    )
    is_correct = models.BooleanField()
    awarded_points = models.PositiveSmallIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("answered_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("participant", "question"),
                name="one_contest_answer_per_question",
            )
        ]
