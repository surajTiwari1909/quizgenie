from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from multiplayer import services
from multiplayer.models import Contest, ContestParticipant
from multiplayer.serializers import (
    ContestAnswerSerializer,
    ContestSerializer,
    CreateContestSerializer,
    JoinContestSerializer,
)
from quizzes.models import Quiz


def _contest_queryset():
    return (
        Contest.objects.select_related("quiz", "host")
        .prefetch_related("participants__user", "quiz__questions__answer_options")
        .annotate(participant_answer_count=Count("participants__answers"))
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_contest(request: Request) -> Response:
    serializer = CreateContestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    quiz = get_object_or_404(Quiz, id=serializer.validated_data["quiz_id"], owner=request.user)
    try:
        contest = services.create_contest(
            host=request.user,
            quiz=quiz,
            max_players=serializer.validated_data["max_players"],
        )
    except services.ContestStateError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(
        ContestSerializer(_contest_queryset().get(id=contest.id)).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_contest(request: Request) -> Response:
    serializer = JoinContestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        participant = services.join_contest(
            user=request.user, code=serializer.validated_data["code"]
        )
    except Contest.DoesNotExist:
        return Response({"detail": "Contest not found."}, status=status.HTTP_404_NOT_FOUND)
    except services.ContestStateError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(ContestSerializer(_contest_queryset().get(id=participant.contest_id)).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contest_detail(request: Request, contest_id: int) -> Response:
    contest = get_object_or_404(_contest_queryset(), id=contest_id, participants__user=request.user)
    return Response(ContestSerializer(contest).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_contest(request: Request, contest_id: int) -> Response:
    contest = get_object_or_404(Contest, id=contest_id)
    try:
        contest = services.start_contest(contest=contest, user=request.user)
    except services.ContestStateError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(ContestSerializer(_contest_queryset().get(id=contest.id)).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def contest_answer(request: Request, contest_id: int) -> Response:
    serializer = ContestAnswerSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    participant = get_object_or_404(ContestParticipant, contest_id=contest_id, user=request.user)
    try:
        services.submit_contest_answer(
            participant=participant,
            question_id=serializer.validated_data["question_id"],
            selected_option_id=serializer.validated_data["answer_option_id"],
        )
    except services.ContestAnswerError as error:
        return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except services.ContestStateError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(ContestSerializer(_contest_queryset().get(id=contest_id)).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def finish_contest(request: Request, contest_id: int) -> Response:
    contest = get_object_or_404(Contest, id=contest_id)
    try:
        services.finish_contest(contest=contest, user=request.user)
    except services.ContestStateError as error:
        return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
    return Response(ContestSerializer(_contest_queryset().get(id=contest_id)).data)
