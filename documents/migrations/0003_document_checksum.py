import hashlib

from django.db import migrations, models
from django.db.models import Q


def populate_document_checksums(apps, _schema_editor):
    document_model = apps.get_model("documents", "Document")
    seen_checksums = set()
    for document in document_model.objects.exclude(file="").iterator():
        try:
            with document.file.open("rb") as stored_file:
                checksum = hashlib.sha256()
                while chunk := stored_file.read(64 * 1024):
                    checksum.update(chunk)
        except OSError:
            continue

        owner_checksum = (document.owner_id, checksum.hexdigest())
        if owner_checksum in seen_checksums:
            continue
        seen_checksums.add(owner_checksum)
        document.checksum_sha256 = owner_checksum[1]
        document.save(update_fields=["checksum_sha256"])


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0002_documentcontent_private_storage"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="checksum_sha256",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.RunPython(populate_document_checksums, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="document",
            constraint=models.UniqueConstraint(
                condition=~Q(checksum_sha256=""),
                fields=("owner", "checksum_sha256"),
                name="unique_document_checksum_per_owner",
            ),
        ),
    ]
