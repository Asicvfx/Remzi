from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.chunks.models import DocumentChunk
from apps.common.text import repair_mojibake
from apps.documents.models import Document, DocumentStatus
from apps.search.embeddings import (
    LOCAL_HASHING_EMBEDDING_DIMENSIONS,
    LocalHashingEmbeddingProvider,
    cosine_similarity,
)
from apps.search.services import SearchChunksService


User = get_user_model()


class LocalHashingEmbeddingProviderTests(TestCase):
    def test_embed_returns_stable_normalized_vector(self):
        provider = LocalHashingEmbeddingProvider()

        first = provider.embed("remzi document search")
        second = provider.embed("remzi document search")

        self.assertEqual(first, second)
        self.assertEqual(len(first), LOCAL_HASHING_EMBEDDING_DIMENSIONS)
        self.assertGreater(cosine_similarity(first, second), 0.99)


class SearchApiTests(APITestCase):
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

    def test_search_returns_matching_chunks_for_current_user(self):
        _, matching_chunk = self.create_chunk(
            self.user,
            "Python Guide",
            "Python Django REST API authentication and documents",
        )
        self.create_chunk(
            self.user,
            "Cooking Guide",
            "Bread butter kitchen recipe",
        )

        response = self.client.post(
            reverse("search:search"),
            {"query": "Django API documents", "limit": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["document_id"])
        self.assertGreaterEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["chunk_id"], matching_chunk.id)
        self.assertGreater(response.data["results"][0]["score"], 0)

    def test_search_can_be_filtered_to_one_document(self):
        matching_document, matching_chunk = self.create_chunk(
            self.user,
            "Django Guide",
            "django api document search",
        )
        self.create_chunk(
            self.user,
            "Other Guide",
            "django api document search",
        )

        response = self.client.post(
            reverse("search:search"),
            {
                "query": "django document",
                "limit": 5,
                "document_id": matching_document.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_id"], matching_document.id)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["chunk_id"], matching_chunk.id)

    def test_search_does_not_return_other_users_chunks(self):
        self.create_chunk(
            self.other_user,
            "Private Guide",
            "secret oncology notes and private document",
        )

        response = self.client.post(
            reverse("search:search"),
            {"query": "secret oncology", "limit": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_search_service_respects_limit(self):
        for index in range(3):
            self.create_chunk(
                self.user,
                f"Guide {index}",
                "django api document search",
            )

        results = SearchChunksService.execute(
            user=self.user,
            query="django document",
            limit=2,
        )

        self.assertEqual(len(results), 2)

    def test_search_response_truncates_large_chunk_text(self):
        long_text = "django " * 500
        self.create_chunk(self.user, "Long Guide", long_text)

        response = self.client.post(
            reverse("search:search"),
            {"query": "django", "limit": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["results"][0]["text"]), 1200)

    def test_search_repairs_mojibake_query_and_result_text(self):
        original_query = "что написано про опыт работы"
        broken_query = original_query.encode("utf-8").decode("cp1251")
        broken_text = "Опыт работы с Python".encode("utf-8").decode("cp1251")
        _, chunk = self.create_chunk(self.user, "CV", broken_text)

        response = self.client.post(
            reverse("search:search"),
            {"query": broken_query, "limit": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["query"], original_query)
        self.assertEqual(response.data["results"][0]["chunk_id"], chunk.id)
        self.assertIn("Опыт работы", response.data["results"][0]["text"])
        self.assertEqual(repair_mojibake(broken_query), original_query)
