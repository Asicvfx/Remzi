from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.chunks.models import DocumentChunk


class DocumentChunkSerializer(serializers.ModelSerializer):
    embedding_dimensions = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChunk
        fields = (
            "id",
            "document",
            "chunk_index",
            "text",
            "page_number",
            "token_count",
            "embedding_model",
            "embedding_dimensions",
            "embedded_at",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.INT)
    def get_embedding_dimensions(self, obj):
        return len(obj.embedding or [])
