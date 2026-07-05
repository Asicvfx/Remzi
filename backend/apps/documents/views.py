from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer
from apps.documents.services import CreateDocumentService


@extend_schema_view(
    post=extend_schema(
        summary="Upload a document",
        description="Uploads a PDF, DOCX, or TXT file for the authenticated user and queues background processing.",
        request=DocumentUploadSerializer,
        responses={201: DocumentSerializer},
    )
)
class DocumentUploadView(generics.CreateAPIView):
    serializer_class = DocumentUploadSerializer
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = CreateDocumentService.execute(
            user=request.user,
            validated_data=serializer.validated_data.copy(),
        )
        response_serializer = DocumentSerializer(
            document, context=self.get_serializer_context()
        )
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


@extend_schema(
    summary="List current user's documents",
    description="Returns only the authenticated user's uploaded documents.",
)
class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Get document details",
        description="Returns a single document owned by the authenticated user.",
    ),
    delete=extend_schema(
        summary="Delete a document",
        description="Deletes a document owned by the authenticated user.",
    ),
)
class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)
