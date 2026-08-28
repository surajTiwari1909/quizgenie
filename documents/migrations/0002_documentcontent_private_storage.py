import shutil
from pathlib import Path

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import documents.models
import documents.storage
import documents.validators


def move_document_files(apps, _schema_editor):
    document_model = apps.get_model("documents", "Document")
    _move_files(document_model, Path(settings.MEDIA_ROOT), Path(settings.DOCUMENT_ROOT))


def restore_document_files(apps, _schema_editor):
    document_model = apps.get_model("documents", "Document")
    _move_files(document_model, Path(settings.DOCUMENT_ROOT), Path(settings.MEDIA_ROOT))


def _move_files(document_model, source_root: Path, destination_root: Path):
    for document in document_model.objects.exclude(file="").iterator():
        relative_path = Path(document.file.name)
        source = source_root / relative_path
        destination = destination_root / relative_path
        if not source.is_file():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)
        source.unlink()


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_document_files, restore_document_files),
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(
                storage=documents.storage.PrivateDocumentStorage(),
                upload_to=documents.models.document_upload_path,
                validators=[documents.validators.validate_pdf_document],
            ),
        ),
        migrations.CreateModel(
            name="DocumentContent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.TextField()),
                ("page_count", models.PositiveIntegerField()),
                ("character_count", models.PositiveBigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content",
                        to="documents.document",
                    ),
                ),
            ],
        ),
    ]
