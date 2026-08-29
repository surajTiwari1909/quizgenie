from django.conf import settings
from django.db import models
from django.db.models import Q

from quizzes.models import AnswerOption, Question, Quiz


class SoloAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solo_attempts",
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="solo_attempts",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField()
    question_count = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-started_at", "-id")
        indexes = [
            models.Index(fields=("user", "status"), name="solo_user_status_idx"),
            models.Index(fields=("quiz", "started_at"), name="solo_quiz_started_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(score__lte=models.F("max_score")),
                name="solo_score_not_above_maximum",
            ),
            models.CheckConstraint(
                condition=Q(question_count__gte=1),
                name="solo_question_count_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.quiz}"


class SoloAnswer(models.Model):
    attempt = models.ForeignKey(
        SoloAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="solo_answers",
    )
    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.SET_NULL,
        related_name="solo_selections",
        blank=True,
        null=True,
    )
    is_correct = models.BooleanField()
    awarded_points = models.PositiveSmallIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("answered_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "question"),
                name="one_answer_per_solo_attempt_question",
            )
        ]

    def __str__(self) -> str:
        return f"Answer to question {self.question_id} in attempt {self.attempt_id}"

