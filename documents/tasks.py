from celery import shared_task
from django.conf import settings

from documents import services


@shared_task(
    ignore_result=True,
    soft_time_limit=settings.DOCUMENT_PROCESSING_SOFT_TIME_LIMIT,
    time_limit=settings.DOCUMENT_PROCESSING_TIME_LIMIT,
)
def process_document_task(document_id: int) -> None:
    services.process_document(document_id)
