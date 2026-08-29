from rest_framework import serializers

from multiplayer.models import Contest, ContestParticipant
from quizzes.models import AnswerOption, Question


class CreateContestSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(min_value=1)
    max_players = serializers.IntegerField(min_value=2, max_value=100, default=20)


class JoinContestSerializer(serializers.Serializer):
    code = serializers.RegexField(regex=r"^[A-Za-z0-9]{8}$")


class ContestAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    answer_option_id = serializers.IntegerField(min_value=1)


class ContestParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    answered_count = serializers.SerializerMethodField()

    class Meta:
        model = ContestParticipant
        fields = ("user_id", "username", "score", "answered_count", "joined_at")
        read_only_fields = fields

    def get_answered_count(self, participant: ContestParticipant) -> int:
        return getattr(participant, "answer_count", participant.answers.count())


class ContestOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ("id", "text", "order")
        read_only_fields = fields


class ContestQuestionSerializer(serializers.ModelSerializer):
    answer_options = ContestOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "order", "points", "answer_options")
        read_only_fields = fields


class ContestSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    participants = ContestParticipantSerializer(many=True, read_only=True)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = (
            "id",
            "code",
            "quiz_id",
            "quiz_title",
            "status",
            "max_players",
            "participants",
            "questions",
            "created_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = fields

    def get_questions(self, contest: Contest) -> list[dict]:
        if contest.status == Contest.Status.WAITING:
            return []
        return ContestQuestionSerializer(contest.quiz.questions.all(), many=True).data
