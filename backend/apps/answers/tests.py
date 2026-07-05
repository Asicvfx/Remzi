from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.answers.llm import GeneratedAnswer
from apps.answers.services import AskQuestionService, LocalExtractiveAnswerComposer
from apps.chunks.models import DocumentChunk
from apps.documents.models import Document, DocumentStatus
from apps.search.embeddings import LocalHashingEmbeddingProvider


User = get_user_model()


class LocalExtractiveAnswerComposerTests(TestCase):
    def test_compose_returns_empty_answer_without_context(self):
        answer = LocalExtractiveAnswerComposer.compose(
            question="что написано про опыт работы",
            search_results=[],
        )

        self.assertIn("не нашёл", answer)

    def test_compose_returns_short_bullets(self):
        answer = LocalExtractiveAnswerComposer.compose(
            question="что написано про опыт работы",
            search_results=[
                {
                    "score": 0.9,
                    "text": "Опыт работы включает Python и Django; знание REST API; PostgreSQL; командная разработка и CI/CD.",
                }
            ],
        )

        self.assertIn("- Опыт работы включает Python и Django", answer)
        self.assertLess(len(answer), 500)


class AskApiTests(APITestCase):
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

    def create_chunk(self, user, title, text):
        document = Document.objects.create(
            user=user,
            title=title,
            file=SimpleUploadedFile("source.txt", text.encode("utf-8")),
            file_type="txt",
            status=DocumentStatus.READY,
            extracted_text=text,
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            text=text,
            token_count=len(text.split()),
            embedding=self.provider.embed(text),
            embedding_model=self.provider.model_name,
            embedded_at=timezone.now(),
        )
        return document, chunk

    def test_ask_returns_answer_with_citations(self):
        document, chunk = self.create_chunk(
            self.user,
            "CV",
            "Опыт работы включает Python Django REST API и PostgreSQL.",
        )

        response = self.client.post(
            reverse("answers:ask"),
            {
                "question": "что написано про опыт работы",
                "limit": 3,
                "document_id": document.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_id"], document.id)
        self.assertEqual(response.data["answer_mode"], "local")
        self.assertEqual(response.data["model"], "")
        self.assertIn("По найденным фрагментам", response.data["answer"])
        self.assertIn("- ", response.data["answer"])
        self.assertEqual(len(response.data["citations"]), 1)
        self.assertEqual(response.data["citations"][0]["chunk_id"], chunk.id)
        self.assertIn("Python Django", response.data["citations"][0]["text"])

    def test_ask_does_not_use_other_users_documents(self):
        self.create_chunk(
            self.other_user,
            "Private CV",
            "secret Python Django experience",
        )

        response = self.client.post(
            reverse("answers:ask"),
            {"question": "Python Django", "limit": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer_mode"], "local")
        self.assertEqual(response.data["citations"], [])
        self.assertIn("could not find", response.data["answer"])

    def test_ask_service_returns_same_shape(self):
        document, _ = self.create_chunk(
            self.user,
            "Guide",
            "Django API documents and authentication",
        )

        payload = AskQuestionService.execute(
            user=self.user,
            question="Django API",
            limit=2,
            document_id=document.id,
        )

        self.assertEqual(payload["document_id"], document.id)
        self.assertIn("answer", payload)
        self.assertEqual(payload["answer_mode"], "local")
        self.assertEqual(payload["model"], "")
        self.assertEqual(len(payload["citations"]), 1)

    def test_ask_trims_long_citation_text(self):
        document, _ = self.create_chunk(
            self.user,
            "Long Guide",
            "Django " * 300,
        )

        response = self.client.post(
            reverse("answers:ask"),
            {"question": "Django", "limit": 1, "document_id": document.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["citations"][0]["text"]), 700)

    @override_settings(
        OPENAI_ANSWER_ENABLED=True,
        OPENAI_API_KEY="test-key",
        LLM_MODEL="gpt-test",
    )
    @patch("apps.answers.services.OpenAIAnswerClient.generate_answer")
    def test_ask_uses_openai_answer_when_configured(self, mock_generate_answer):
        mock_generate_answer.return_value = GeneratedAnswer(
            answer="LLM answer from citations.",
            model="gpt-test",
        )
        document, _ = self.create_chunk(
            self.user,
            "Guide",
            "Django API documents and authentication",
        )

        response = self.client.post(
            reverse("answers:ask"),
            {"question": "Django API", "limit": 1, "document_id": document.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "LLM answer from citations.")
        self.assertEqual(response.data["answer_mode"], "openai")
        self.assertEqual(response.data["model"], "gpt-test")
        mock_generate_answer.assert_called_once()
