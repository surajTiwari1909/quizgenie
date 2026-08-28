from django.apps import AppConfig
from django.utils.module_loading import import_string


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"

    def ready(self) -> None:
        import_string("documents.signals.delete_stored_document_file")
