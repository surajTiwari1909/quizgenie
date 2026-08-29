import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from documents.models import Document
from quizzes.models import AnswerOption, Question, Quiz

pytestmark = pytest.mark.django_db


def create_document(owner, filename="notes.pdf") -> Document:
    return Document.objects.create(
        owner=owner,
        file=SimpleUploadedFile(filename, b"%PDF-1.4\n%%EOF"),
        original_filename=filename,
        content_type="application/pdf",
        file_size=15,
    )


def test_quiz_defaults_and_relationships() -> None:
    user = get_user_model().objects.create_user(username="learner")
    document = create_document(user)

    quiz = Quiz.objects.create(owner=user, source_document=document, title="Biology")
    question = Question.objects.create(quiz=quiz, text="What is a cell?", order=1)
    answer = AnswerOption.objects.create(
        question=question,
        text="The basic unit of life",
        is_correct=True,
        order=1,
    )

    assert quiz.difficulty == Quiz.Difficulty.MEDIUM
    assert quiz.status == Quiz.Status.DRAFT
    assert list(quiz.questions.all()) == [question]
    assert list(question.answer_options.all()) == [answer]


def test_source_document_must_belong_to_quiz_owner() -> None:
    quiz_owner = get_user_model().objects.create_user(username="quiz-owner")
    document_owner = get_user_model().objects.create_user(username="document-owner")
    document = create_document(document_owner)
    quiz = Quiz(owner=quiz_owner, source_document=document, title="Biology")

    with pytest.raises(ValidationError, match="must belong to the quiz owner"):
        quiz.full_clean()


def test_deleting_source_document_preserves_quiz() -> None:
    user = get_user_model().objects.create_user(username="learner")
    document = create_document(user)
    quiz = Quiz.objects.create(owner=user, source_document=document, title="Biology")

    document.delete()

    quiz.refresh_from_db()
    assert quiz.source_document is None


def test_deleting_owner_cascades_through_quiz_content() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz = Quiz.objects.create(owner=user, title="Biology")
    question = Question.objects.create(quiz=quiz, text="What is a cell?", order=1)
    AnswerOption.objects.create(question=question, text="An organ", order=1)

    user.delete()

    assert not Quiz.objects.filter(id=quiz.id).exists()
    assert not Question.objects.filter(id=question.id).exists()
    assert not AnswerOption.objects.filter(question_id=question.id).exists()


def test_questions_are_ordered_and_order_is_unique_within_quiz() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz = Quiz.objects.create(owner=user, title="Biology")
    second = Question.objects.create(quiz=quiz, text="Second", order=2)
    first = Question.objects.create(quiz=quiz, text="First", order=1)

    assert list(quiz.questions.all()) == [first, second]

    with pytest.raises(IntegrityError), transaction.atomic():
        Question.objects.create(quiz=quiz, text="Duplicate", order=1)


def test_answer_options_are_ordered_and_allow_only_one_correct_answer() -> None:
    user = get_user_model().objects.create_user(username="learner")
    quiz = Quiz.objects.create(owner=user, title="Biology")
    question = Question.objects.create(quiz=quiz, text="What is a cell?", order=1)
    second = AnswerOption.objects.create(question=question, text="An organ", order=2)
    first = AnswerOption.objects.create(
        question=question,
        text="The basic unit of life",
        is_correct=True,
        order=1,
    )

    assert list(question.answer_options.all()) == [first, second]

    with pytest.raises(IntegrityError), transaction.atomic():
        AnswerOption.objects.create(
            question=question,
            text="A second correct answer",
            is_correct=True,
            order=3,
        )

