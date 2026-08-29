from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Quiz(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    source_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        related_name="quizzes",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("owner", "status"), name="quiz_owner_status_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        if (
            self.source_document_id
            and self.owner_id
            and self.source_document.owner_id != self.owner_id
        ):
            raise ValidationError(
                {"source_document": "The source document must belong to the quiz owner."}
            )


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField()
    points = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("quiz", "order"),
                name="unique_question_order_per_quiz",
            ),
            models.CheckConstraint(
                condition=Q(order__gte=1),
                name="question_order_at_least_one",
            ),
            models.CheckConstraint(
                condition=Q(points__gte=1),
                name="question_points_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return self.text


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answer_options",
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("question", "order"),
                name="unique_answer_order_per_question",
            ),
            models.UniqueConstraint(
                fields=("question",),
                condition=Q(is_correct=True),
                name="one_correct_answer_per_question",
            ),
            models.CheckConstraint(
                condition=Q(order__gte=1),
                name="answer_order_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return self.text
