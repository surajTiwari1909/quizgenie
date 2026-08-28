from django.urls import path

from documents import views

urlpatterns = [
    path("", views.document_collection, name="document-list"),
    path("<int:document_id>", views.document_detail, name="document-detail"),
]
