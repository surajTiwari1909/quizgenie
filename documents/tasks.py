from celery import shared_task

from documents import services


@shared_task(ignore_result=True)
def process_document_task(document_id: int) -> None:
    services.process_document(document_id)
