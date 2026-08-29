from celery import shared_task
from django.conf import settings

from quizzes import services


@shared_task(
    ignore_result=True,
    soft_time_limit=settings.QUIZ_GENERATION_SOFT_TIME_LIMIT,
    time_limit=settings.QUIZ_GENERATION_TIME_LIMIT,
)
def generate_topic_quiz_task(quiz_id: int) -> None:
    services.process_topic_quiz(quiz_id)

