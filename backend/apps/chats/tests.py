from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.answers.llm import GeneratedAnswer
from apps.chunks.models import DocumentChunk
from apps.documents.models import Document, DocumentStatus
from apps.search.embeddings import LocalHashingEmbeddingProvider


User = get_user_model()


class ChatApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="StrongPass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongPass123",
        )
        self.client.force_authenticate(user=self.user)
        self.provider = LocalHashingEmbeddingProvider()

    def create_document_with_chunk(self, user, title="CV"):
        text = "Опыт работы включает Python Django REST API и PostgreSQL."
        document = Document.objects.create(
            user=user,
            title=title,
            file=SimpleUploadedFile("source.txt", text.encode("utf-8")),
            file_type="txt",
            status=DocumentStatus.READY,
            extracted_text=text,
        )
        DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            text=text,
            token_count=len(text.split()),
            embedding=self.provider.embed(text),
            embedding_model=self.provider.model_name,
            embedded_at=timezone.now(),
        )
        return document

    def test_create_chat_session(self):
        document = self.create_document_with_chunk(self.user)

        response = self.client.post(
            reverse("chats:list_create"),
            {"title": "CV chat", "document_id": document.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "CV chat")
        self.assertEqual(response.data["document_id"], document.id)
        self.assertEqual(response.data["message_count"], 0)

    def test_ask_in_chat_persists_message(self):
        document = self.create_document_with_chunk(self.user)
        session_response = self.client.post(
            reverse("chats:list_create"),
            {"document_id": document.id},
            format="json",
        )
        session_id = session_response.data["id"]

        response = self.client.post(
            reverse("chats:ask", kwargs={"pk": session_id}),
            {"question": "что написано про опыт работы", "limit": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["session"]["id"], session_id)
        self.assertEqual(response.data["session"]["message_count"], 1)
        self.assertEqual(response.data["message"]["document_id"], document.id)
        self.assertEqual(response.data["message"]["answer_mode"], "local")
        self.assertIn("По найденным фрагментам", response.data["message"]["answer"])
        self.assertEqual(len(response.data["message"]["citations"]), 1)

        messages_response = self.client.get(
            reverse("chats:messages", kwargs={"pk": session_id}),
        )
        self.assertEqual(messages_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(messages_response.data), 1)
        self.assertEqual(messages_response.data[0]["question"], "что написано про опыт работы")

    @override_settings(
        OPENAI_ANSWER_ENABLED=True,
        OPENAI_API_KEY="test-key",
        LLM_MODEL="gpt-test",
    )
    @patch("apps.answers.services.OpenAIAnswerClient.generate_answer")
    def test_ask_in_chat_stores_openai_answer(self, mock_generate_answer):
        mock_generate_answer.return_value = GeneratedAnswer(
            answer="LLM answer from citations.",
            model="gpt-test",
        )
        document = self.create_document_with_chunk(self.user)
        session_response = self.client.post(
            reverse("chats:list_create"),
            {"document_id": document.id},
            format="json",
        )

        response = self.client.post(
            reverse("chats:ask", kwargs={"pk": session_response.data["id"]}),
            {"question": "Django API", "limit": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"]["answer"], "LLM answer from citations.")
        self.assertEqual(response.data["message"]["answer_mode"], "openai")
        self.assertEqual(response.data["message"]["model"], "gpt-test")

    def test_other_user_cannot_access_chat(self):
        document = self.create_document_with_chunk(self.user)
        session_response = self.client.post(
            reverse("chats:list_create"),
            {"document_id": document.id},
            format="json",
        )
        self.client.force_authenticate(user=self.other_user)

        detail_response = self.client.get(
            reverse("chats:detail", kwargs={"pk": session_response.data["id"]}),
        )
        ask_response = self.client.post(
            reverse("chats:ask", kwargs={"pk": session_response.data["id"]}),
            {"question": "secret", "limit": 1},
            format="json",
        )

        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(ask_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_create_chat_for_other_users_document(self):
        document = self.create_document_with_chunk(self.other_user)

        response = self.client.post(
            reverse("chats:list_create"),
            {"document_id": document.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
