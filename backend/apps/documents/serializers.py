from pathlib import Path

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.documents.models import Document, DocumentStatus


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}


class DocumentSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(read_only=True)
    extracted_text_length = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()
    text_preview = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "filename",
            "file",
            "file_type",
            "status",
            "error_message",
            "extracted_text_length",
            "chunk_count",
            "text_preview",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.INT)
    def get_extracted_text_length(self, obj):
        return len(obj.extracted_text or "")

    @extend_schema_field(OpenApiTypes.INT)
    def get_chunk_count(self, obj):
        if not obj.pk:
            return 0
        return obj.chunks.count()

    @extend_schema_field(OpenApiTypes.STR)
    def get_text_preview(self, obj):
        if not obj.extracted_text:
            return ""
        return obj.extracted_text[:300]


class DocumentUploadSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Document
        fields = ("id", "title", "file")
        read_only_fields = ("id",)

    def validate_file(self, value):
        suffix = Path(value.name).suffix.lower()
        if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise serializers.ValidationError(
                "Unsupported file type. Only PDF, DOCX, and TXT are allowed."
            )
        return value

    def validate(self, attrs):
        uploaded_file = attrs["file"]
        title = attrs.get("title", "").strip()
        attrs["title"] = title or Path(uploaded_file.name).stem
        attrs["file_type"] = Path(uploaded_file.name).suffix.lower().lstrip(".")
        attrs["status"] = DocumentStatus.UPLOADED
        return attrs
