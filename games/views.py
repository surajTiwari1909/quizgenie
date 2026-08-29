from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from games import services
from games.models import SoloAnswer, SoloAttempt
from games.serializers import (
    SoloAttemptSerializer,
    StartSoloAttemptSerializer,
    SubmitSoloAnswerSerializer,
)
from quizzes.models import AnswerOption, Question, Quiz


def _attempt_queryset():
    return SoloAttempt.objects.select_related("quiz").prefetch_related(
        Prefetch(
            "quiz__questions",
            queryset=Question.objects.prefetch_related(
                Prefetch("answer_options", queryset=AnswerOption.objects.order_by("order"))
            ).order_by("order"),
        ),
        Prefetch(
            "answers",
            queryset=SoloAnswer.objects.select_related("question", "selected_option"),
        ),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_solo_attempt(request: Request) -> Response:
    serializer = StartSoloAttemptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    quiz = get_object_or_404(
        Quiz,
        id=serializer.validated_data["quiz_id"],
        owner=request.user,
    )
    try:
        attempt = services.start_solo_attempt(user=request.user, quiz=quiz)
    except services.InvalidQuizForGameplay as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    attempt = get_object_or_404(_attempt_queryset(), id=attempt.id)
    return Response(SoloAttemptSerializer(attempt).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def solo_attempt_detail(request: Request, attempt_id: int) -> Response:
    attempt = get_object_or_404(_attempt_queryset(), id=attempt_id, user=request.user)
    return Response(SoloAttemptSerializer(attempt).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_solo_answer(request: Request, attempt_id: int) -> Response:
    serializer = SubmitSoloAnswerSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    attempt = get_object_or_404(SoloAttempt, id=attempt_id, user=request.user)
    try:
        services.submit_solo_answer(
            attempt=attempt,
            question_id=serializer.validated_data["question_id"],
            selected_option_id=serializer.validated_data["answer_option_id"],
        )
    except services.InvalidAnswer as error:
        return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except services.InvalidAttemptState as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

    refreshed_attempt = get_object_or_404(_attempt_queryset(), id=attempt.id)
    return Response(SoloAttemptSerializer(refreshed_attempt).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_solo_attempt(request: Request, attempt_id: int) -> Response:
    attempt = get_object_or_404(SoloAttempt, id=attempt_id, user=request.user)
    try:
        services.complete_solo_attempt(attempt)
    except services.InvalidAttemptState as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    completed_attempt = get_object_or_404(_attempt_queryset(), id=attempt.id)
    return Response(SoloAttemptSerializer(completed_attempt).data)

