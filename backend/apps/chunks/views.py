from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics

from apps.chunks.serializers import DocumentChunkSerializer
from apps.documents.models import Document


@extend_schema(
    summary="List document chunks",
    description="Returns text chunks generated from a processed document owned by the authenticated user.",
)
class DocumentChunkListView(generics.ListAPIView):
    serializer_class = DocumentChunkSerializer

    def get_queryset(self):
        document = get_object_or_404(
            Document.objects.filter(user=self.request.user),
            id=self.kwargs["document_id"],
        )
        return document.chunks.all()
