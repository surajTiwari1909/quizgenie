from django.urls import path

from documents import views

urlpatterns = [
    path("", views.document_collection, name="document-list"),
    path("<int:document_id>", views.document_detail, name="document-detail"),
    path("<int:document_id>/content", views.document_content, name="document-content"),
    path("<int:document_id>/download", views.document_download, name="document-download"),
    path("<int:document_id>/retry", views.document_retry, name="document-retry"),
]
