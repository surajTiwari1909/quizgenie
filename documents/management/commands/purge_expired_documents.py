from django.core.management.base import BaseCommand

from documents.services import delete_expired_documents


class Command(BaseCommand):
    help = "Delete documents older than DOCUMENT_RETENTION_DAYS and their stored files."

    def handle(self, *_args, **_options) -> None:
        deleted_count = delete_expired_documents()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} expired document(s)."))
