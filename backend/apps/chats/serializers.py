from rest_framework import serializers

from apps.documents.models import Document
from apps.chats.models import ChatMessage, ChatSession


class ChatSessionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=160, required=False, allow_blank=True)
    document_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)

    def validate_document_id(self, value):
        if value is None:
            return value
        user = self.context["request"].user
        if not Document.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("Document not found.")
        return value


class ChatSessionSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="document.id", allow_null=True, read_only=True)
    document_title = serializers.CharField(source="document.title", allow_null=True, read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatSession
        fields = (
            "id",
            "title",
            "document_id",
            "document_title",
            "message_count",
            "created_at",
            "updated_at",
        )


class ChatMessageSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="document.id", allow_null=True, read_only=True)
    document_title = serializers.CharField(source="document.title", allow_null=True, read_only=True)

    class Meta:
        model = ChatMessage
        fields = (
            "id",
            "question",
            "answer",
            "answer_mode",
            "model",
            "document_id",
            "document_title",
            "citations",
            "created_at",
        )


class ChatAskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)
    limit = serializers.IntegerField(default=5, min_value=1, max_value=10)
    document_id = serializers.IntegerField(required=False, min_value=1, allow_null=True)

    def validate_document_id(self, value):
        if value is None:
            return value
        user = self.context["request"].user
        if not Document.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("Document not found.")
        return value


class ChatAskResponseSerializer(serializers.Serializer):
    session = ChatSessionSerializer()
    message = ChatMessageSerializer()
