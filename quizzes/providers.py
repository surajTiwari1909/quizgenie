import json
from typing import Protocol

from django.conf import settings

from quizzes.validation import GeneratedAnswerOption, GeneratedQuestion


class QuestionGenerator(Protocol):
    def generate_questions(
        self,
        *,
        topic: str,
        difficulty: str,
        question_count: int,
    ) -> list[GeneratedQuestion]: ...

    def regenerate_question(
        self,
        *,
        topic: str,
        difficulty: str,
        question: GeneratedQuestion | None,
        errors: tuple[str, ...],
    ) -> GeneratedQuestion: ...


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "is_correct": {"type": "boolean"},
    },
    "required": ["text", "is_correct"],
    "additionalProperties": False,
}

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "explanation": {"type": "string"},
        "points": {"type": "integer", "minimum": 1, "maximum": 100},
        "options": {
            "type": "array",
            "items": ANSWER_SCHEMA,
            "minItems": 2,
            "maxItems": 6,
        },
    },
    "required": ["text", "explanation", "points", "options"],
    "additionalProperties": False,
}


class GroqQuestionGenerator:
    """Generate schema-constrained quiz questions through the Groq Chat API."""

    def __init__(self) -> None:
        from groq import Groq

        self.client = Groq(
            api_key=settings.GROQ_API_KEY or None,
            timeout=settings.QUIZ_GENERATION_REQUEST_TIMEOUT,
        )

    def generate_questions(
        self,
        *,
        topic: str,
        difficulty: str,
        question_count: int,
    ) -> list[GeneratedQuestion]:
        schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": QUESTION_SCHEMA,
                    "minItems": question_count,
                    "maxItems": question_count,
                }
            },
            "required": ["questions"],
            "additionalProperties": False,
        }
        payload = self._request(
            prompt=(
                f"Create {question_count} {difficulty} multiple-choice quiz questions "
                f"about this topic: {topic}"
            ),
            schema=schema,
            schema_name="topic_quiz",
        )
        return [_deserialize_question(item) for item in payload["questions"]]

    def regenerate_question(
        self,
        *,
        topic: str,
        difficulty: str,
        question: GeneratedQuestion | None,
        errors: tuple[str, ...],
    ) -> GeneratedQuestion:
        previous = "No usable question was returned."
        if question is not None:
            previous = json.dumps(_serialize_question(question), ensure_ascii=False)
        payload = self._request(
            prompt=(
                f"Create one replacement {difficulty} multiple-choice question about {topic}. "
                f"Do not repeat this invalid candidate: {previous}. "
                f"Correct these validation errors: {'; '.join(errors)}"
            ),
            schema=QUESTION_SCHEMA,
            schema_name="replacement_question",
        )
        return _deserialize_question(payload)

    def _request(self, *, prompt: str, schema: dict, schema_name: str) -> dict:
        response = self.client.chat.completions.create(
            model=settings.GROQ_QUIZ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You create accurate, unambiguous educational multiple-choice questions. "
                        "Exactly one option must be correct. Distractors must be plausible "
                        "but false."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("The quiz provider returned no structured output.")
        return json.loads(content)


def _deserialize_question(data: dict) -> GeneratedQuestion:
    return GeneratedQuestion(
        text=data["text"],
        explanation=data["explanation"],
        points=data["points"],
        options=tuple(
            GeneratedAnswerOption(text=option["text"], is_correct=option["is_correct"])
            for option in data["options"]
        ),
    )


def _serialize_question(question: GeneratedQuestion) -> dict:
    return {
        "text": question.text,
        "explanation": question.explanation,
        "points": question.points,
        "options": [
            {"text": option.text, "is_correct": option.is_correct}
            for option in question.options
        ],
    }
