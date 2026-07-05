from django.urls import path

from apps.chunks.views import DocumentChunkListView
from apps.documents.views import (
    DocumentDetailView,
    DocumentListView,
    DocumentUploadView,
)


app_name = "documents"

urlpatterns = [
    path("upload/", DocumentUploadView.as_view(), name="upload"),
    path("", DocumentListView.as_view(), name="list"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="detail"),
    path("<int:document_id>/chunks/", DocumentChunkListView.as_view(), name="chunks"),
]
