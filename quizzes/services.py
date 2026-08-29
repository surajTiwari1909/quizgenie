import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from quizzes.models import AnswerOption, Question, Quiz
from quizzes.providers import QuestionGenerator
from quizzes.validation import GeneratedQuestion, validate_generated_question

logger = logging.getLogger(__name__)


class QuizGenerationError(Exception):
    """A safe, user-facing quiz generation failure."""


class InvalidQuizState(Exception):
    """The requested quiz operation is invalid for its current state."""


def create_topic_quiz(
    *,
    owner: Any,
    topic: str,
    title: str,
    difficulty: str,
    question_count: int,
) -> Quiz:
    with transaction.atomic():
        quiz = Quiz.objects.create(
            owner=owner,
            title=title or topic,
            topic=topic,
            difficulty=difficulty,
            requested_question_count=question_count,
            status=Quiz.Status.GENERATING,
        )
        transaction.on_commit(lambda: enqueue_quiz_generation(quiz.id))
    return quiz


def create_document_quiz(
    *,
    owner: Any,
    document: Any,
    title: str,
    difficulty: str,
    question_count: int,
) -> Quiz:
    if document.status != "ready" or not hasattr(document, "content"):
        raise InvalidQuizState("Only documents with ready extracted content can generate quizzes.")
    with transaction.atomic():
        quiz = Quiz.objects.create(
            owner=owner,
            source_document=document,
            title=title or document.original_filename,
            topic=document.original_filename,
            difficulty=difficulty,
            requested_question_count=question_count,
            status=Quiz.Status.GENERATING,
        )
        transaction.on_commit(lambda: enqueue_quiz_generation(quiz.id))
    return quiz


def process_topic_quiz(quiz_id: int, *, generator: QuestionGenerator | None = None) -> None:
    try:
        quiz = Quiz.objects.get(id=quiz_id)
        if quiz.status == Quiz.Status.READY:
            return
        if not quiz.topic:
            raise QuizGenerationError("A topic is required to generate this quiz.")

        active_generator = generator or get_question_generator()
        candidates = active_generator.generate_questions(
            topic=quiz.topic,
            difficulty=quiz.difficulty,
            question_count=quiz.requested_question_count,
            context=(quiz.source_document.content.text if quiz.source_document_id else None),
        )
        validated_questions = _validate_and_regenerate_questions(
            quiz=quiz,
            candidates=candidates,
            generator=active_generator,
            context=(quiz.source_document.content.text if quiz.source_document_id else None),
        )
        _persist_generated_questions(quiz_id=quiz.id, questions=validated_questions)
    except Quiz.DoesNotExist:
        return
    except QuizGenerationError as error:
        _mark_quiz_failed(quiz_id, str(error))
    except Exception:
        logger.exception("Unexpected quiz generation failure", extra={"quiz_id": quiz_id})
        _mark_quiz_failed(quiz_id, "Quiz generation failed unexpectedly.")


def retry_quiz_generation(quiz: Quiz) -> Quiz:
    with transaction.atomic():
        locked_quiz = Quiz.objects.select_for_update().get(pk=quiz.pk)
        if locked_quiz.status != Quiz.Status.FAILED or not locked_quiz.topic:
            raise InvalidQuizState("Only failed topic-based quizzes can be retried.")
        locked_quiz.status = Quiz.Status.GENERATING
        locked_quiz.failure_reason = ""
        locked_quiz.save(update_fields=["status", "failure_reason", "updated_at"])
        transaction.on_commit(lambda: enqueue_quiz_generation(locked_quiz.id))
    return locked_quiz


def get_question_generator() -> QuestionGenerator:
    generator_class = import_string(settings.QUIZ_GENERATOR_CLASS)
    return generator_class()


def enqueue_quiz_generation(quiz_id: int) -> None:
    from quizzes.tasks import generate_topic_quiz_task

    try:
        generate_topic_quiz_task.delay(quiz_id)
    except Exception:
        logger.exception("Could not queue quiz generation", extra={"quiz_id": quiz_id})
        _mark_quiz_failed(quiz_id, "Quiz generation could not be queued.")


def _validate_and_regenerate_questions(
    *,
    quiz: Quiz,
    candidates: list[GeneratedQuestion],
    generator: QuestionGenerator,
    context: str | None = None,
) -> list[tuple[GeneratedQuestion, int]]:
    validated: list[tuple[GeneratedQuestion, int]] = []
    max_regenerations = settings.QUIZ_MAX_REGENERATION_ATTEMPTS

    for position in range(quiz.requested_question_count):
        candidate = candidates[position] if position < len(candidates) else None
        errors = (
            validate_generated_question(candidate)
            if candidate is not None
            else ("The provider did not return a question for this position.",)
        )
        attempts = 1

        while errors and attempts <= max_regenerations:
            candidate = generator.regenerate_question(
                topic=quiz.topic,
                difficulty=quiz.difficulty,
                question=candidate,
                errors=errors,
                context=context,
            )
            attempts += 1
            errors = validate_generated_question(candidate)

        if candidate is None or errors:
            raise QuizGenerationError(
                f"Question {position + 1} remained invalid after regeneration."
            )
        validated.append((candidate, attempts))
    return validated


def _persist_generated_questions(
    *,
    quiz_id: int,
    questions: list[tuple[GeneratedQuestion, int]],
) -> None:
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(id=quiz_id)
        quiz.questions.all().delete()
        for question_order, (generated, attempts) in enumerate(questions, start=1):
            question = Question.objects.create(
                quiz=quiz,
                text=generated.text.strip(),
                explanation=generated.explanation.strip(),
                order=question_order,
                points=generated.points,
                generation_attempts=attempts,
            )
            AnswerOption.objects.bulk_create(
                [
                    AnswerOption(
                        question=question,
                        text=option.text.strip(),
                        is_correct=option.is_correct,
                        order=option_order,
                    )
                    for option_order, option in enumerate(generated.options, start=1)
                ]
            )
        quiz.status = Quiz.Status.READY
        quiz.failure_reason = ""
        quiz.save(update_fields=["status", "failure_reason", "updated_at"])


def _mark_quiz_failed(quiz_id: int, reason: str) -> None:
    Quiz.objects.filter(id=quiz_id, status=Quiz.Status.GENERATING).update(
        status=Quiz.Status.FAILED,
        failure_reason=reason[:2_000],
        updated_at=timezone.now(),
    )
