from django.db.models.signals import post_delete
from django.dispatch import receiver

from documents.models import Document


@receiver(post_delete, sender=Document)
def delete_stored_document_file(*, instance: Document, **_kwargs: object) -> None:
    if instance.file:
        instance.file.delete(save=False)
