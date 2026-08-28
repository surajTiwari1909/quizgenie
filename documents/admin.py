from django.contrib import admin

from documents.models import Document, DocumentContent


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


@admin.register(DocumentContent)
class DocumentContentAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "page_count", "character_count", "updated_at")
    search_fields = ("document__original_filename", "document__owner__username")
    raw_id_fields = ("document",)
    readonly_fields = ("created_at", "updated_at")
