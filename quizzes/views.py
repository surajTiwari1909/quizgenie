from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from documents.models import Document
from quizzes import services
from quizzes.models import AnswerOption, Question, Quiz
from quizzes.serializers import (
    DocumentQuizGenerationSerializer,
    QuizSerializer,
    TopicQuizGenerationSerializer,
)


def _quiz_queryset():
    return Quiz.objects.prefetch_related(
        Prefetch(
            "questions",
            queryset=Question.objects.prefetch_related(
                Prefetch("answer_options", queryset=AnswerOption.objects.order_by("order"))
            ).order_by("order"),
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_collection(request: Request) -> Response:
    quizzes = _quiz_queryset().filter(owner=request.user)
    return Response(QuizSerializer(quizzes, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_topic_quiz(request: Request) -> Response:
    serializer = TopicQuizGenerationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    quiz = services.create_topic_quiz(
        owner=request.user,
        topic=data["topic"],
        title=data.get("title", ""),
        difficulty=data["difficulty"],
        question_count=data["question_count"],
    )
    return Response(QuizSerializer(quiz).data, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_document_quiz(request: Request) -> Response:
    serializer = DocumentQuizGenerationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    document = get_object_or_404(
        Document.objects.select_related("content"),
        id=data["document_id"],
        owner=request.user,
    )
    try:
        quiz = services.create_document_quiz(
            owner=request.user,
            document=document,
            title=data.get("title", ""),
            difficulty=data["difficulty"],
            question_count=data["question_count"],
        )
    except services.InvalidQuizState as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(QuizSerializer(quiz).data, status=status.HTTP_202_ACCEPTED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def quiz_manage(request: Request, quiz_id: int) -> Response:
    quiz = get_object_or_404(Quiz, id=quiz_id, owner=request.user)
    if request.method == "DELETE":
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = QuizSerializer(quiz, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(QuizSerializer(quiz).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_detail(request: Request, quiz_id: int) -> Response:
    quiz = get_object_or_404(_quiz_queryset(), id=quiz_id, owner=request.user)
    return Response(QuizSerializer(quiz).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retry_quiz_generation(request: Request, quiz_id: int) -> Response:
    quiz = get_object_or_404(Quiz, id=quiz_id, owner=request.user)
    try:
        quiz = services.retry_quiz_generation(quiz)
    except services.InvalidQuizState as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(QuizSerializer(quiz).data, status=status.HTTP_202_ACCEPTED)
