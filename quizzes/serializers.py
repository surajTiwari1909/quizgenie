from rest_framework import serializers

from quizzes.models import AnswerOption, Question, Quiz


class TopicQuizGenerationSerializer(serializers.Serializer):
    topic = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
    title = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        trim_whitespace=True,
    )
    difficulty = serializers.ChoiceField(
        choices=Quiz.Difficulty.choices,
        default=Quiz.Difficulty.MEDIUM,
    )
    question_count = serializers.IntegerField(min_value=1, max_value=20, default=10)


class DocumentQuizGenerationSerializer(TopicQuizGenerationSerializer):
    document_id = serializers.IntegerField(min_value=1)


class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ("id", "text", "is_correct", "order")
        read_only_fields = fields


class QuestionSerializer(serializers.ModelSerializer):
    answer_options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "text",
            "explanation",
            "order",
            "points",
            "generation_attempts",
            "answer_options",
        )
        read_only_fields = fields


class QuizSerializer(serializers.ModelSerializer):
    source_document_id = serializers.IntegerField(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "description",
            "topic",
            "difficulty",
            "requested_question_count",
            "status",
            "failure_reason",
            "source_document_id",
            "questions",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "topic",
            "requested_question_count",
            "status",
            "failure_reason",
            "source_document_id",
            "questions",
            "created_at",
            "updated_at",
        )
