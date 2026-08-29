from rest_framework import serializers

from games.models import SoloAnswer, SoloAttempt
from quizzes.models import AnswerOption, Question


class StartSoloAttemptSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField(min_value=1)


class SubmitSoloAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    answer_option_id = serializers.IntegerField(min_value=1)


class PlayAnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ("id", "text", "order")
        read_only_fields = fields


class PlayQuestionSerializer(serializers.ModelSerializer):
    answer_options = PlayAnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "order", "points", "answer_options")
        read_only_fields = fields


class SoloAnswerSerializer(serializers.ModelSerializer):
    selected_option_id = serializers.IntegerField(read_only=True)
    correct_option_id = serializers.SerializerMethodField()
    explanation = serializers.CharField(source="question.explanation", read_only=True)

    class Meta:
        model = SoloAnswer
        fields = (
            "question_id",
            "selected_option_id",
            "is_correct",
            "awarded_points",
            "correct_option_id",
            "explanation",
            "answered_at",
        )
        read_only_fields = fields

    def get_correct_option_id(self, answer: SoloAnswer) -> int | None:
        correct = answer.question.answer_options.filter(is_correct=True).first()
        return correct.id if correct else None


class SoloAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    questions = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    answered_count = serializers.SerializerMethodField()

    class Meta:
        model = SoloAttempt
        fields = (
            "id",
            "quiz_id",
            "quiz_title",
            "status",
            "score",
            "max_score",
            "question_count",
            "answered_count",
            "questions",
            "answers",
            "started_at",
            "expires_at",
            "completed_at",
        )
        read_only_fields = fields

    def get_questions(self, attempt: SoloAttempt) -> list[dict]:
        return PlayQuestionSerializer(attempt.quiz.questions.all(), many=True).data

    def get_answers(self, attempt: SoloAttempt) -> list[dict]:
        if attempt.status != SoloAttempt.Status.COMPLETED:
            return []
        return SoloAnswerSerializer(attempt.answers.all(), many=True).data

    def get_answered_count(self, attempt: SoloAttempt) -> int:
        return attempt.answers.count()
