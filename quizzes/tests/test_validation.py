from quizzes.validation import (
    GeneratedAnswerOption,
    GeneratedQuestion,
    validate_generated_question,
)


def test_question_validation_reports_independent_structural_errors() -> None:
    question = GeneratedQuestion(
        text=" ",
        explanation="",
        points=0,
        options=(
            GeneratedAnswerOption(text="Duplicate", is_correct=True),
            GeneratedAnswerOption(text="duplicate", is_correct=True),
        ),
    )

    errors = validate_generated_question(question)

    assert "Question text is required." in errors
    assert "Points must be between 1 and 100." in errors
    assert "Answer options must be unique within a question." in errors
    assert "A question must have exactly one correct answer option." in errors
