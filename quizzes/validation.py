from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedAnswerOption:
    text: str
    is_correct: bool


@dataclass(frozen=True)
class GeneratedQuestion:
    text: str
    explanation: str
    options: tuple[GeneratedAnswerOption, ...]
    points: int = 1


def validate_generated_question(question: GeneratedQuestion) -> tuple[str, ...]:
    """Return every structural error for one generated question."""
    errors: list[str] = []
    text = question.text.strip()
    explanation = question.explanation.strip()

    if not text:
        errors.append("Question text is required.")
    elif len(text) > 2_000:
        errors.append("Question text must be 2,000 characters or fewer.")
    if len(explanation) > 5_000:
        errors.append("Explanation must be 5,000 characters or fewer.")
    if not 1 <= question.points <= 100:
        errors.append("Points must be between 1 and 100.")
    if not 2 <= len(question.options) <= 6:
        errors.append("A question must have between 2 and 6 answer options.")

    normalized_options: list[str] = []
    for option in question.options:
        option_text = option.text.strip()
        if not option_text:
            errors.append("Answer option text is required.")
        elif len(option_text) > 1_000:
            errors.append("Answer option text must be 1,000 characters or fewer.")
        normalized_options.append(option_text.casefold())

    nonempty_options = [option for option in normalized_options if option]
    if len(nonempty_options) != len(set(nonempty_options)):
        errors.append("Answer options must be unique within a question.")
    if sum(option.is_correct for option in question.options) != 1:
        errors.append("A question must have exactly one correct answer option.")
    return tuple(dict.fromkeys(errors))
