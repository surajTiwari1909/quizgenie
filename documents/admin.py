from django.contrib import admin

from documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "owner",
        "status",
        "file_size",
        "created_at",
    )
    list_filter = ("status", "content_type")
    search_fields = ("original_filename", "owner__username", "owner__email")
    raw_id_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
