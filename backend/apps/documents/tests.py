import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from docx import Document as DocxDocument
from rest_framework import status
from rest_framework.test import APITestCase

from apps.chunks.models import DocumentChunk
from apps.documents.extractors import DocumentTextExtractor
from apps.documents.models import Document, DocumentStatus
from apps.documents.tasks import process_document_task


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def make_uploaded_docx(text):
    temp_dir = Path(tempfile.mkdtemp())
    path = temp_dir / "sample.docx"
    document = DocxDocument()
    document.add_paragraph(text)
    document.save(path)
    uploaded_file = SimpleUploadedFile(
        "sample.docx",
        path.read_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    shutil.rmtree(temp_dir, ignore_errors=True)
    return uploaded_file


@override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class DocumentApiTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

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

    @patch("apps.documents.tasks.process_document_task.delay")
    @patch("apps.documents.services.transaction.on_commit")
    def test_upload_document_queues_processing(self, mocked_on_commit, mocked_delay):
        mocked_on_commit.side_effect = lambda fn: fn()
        upload = SimpleUploadedFile(
            "knowledge-base.txt",
            b"Remzi stage 5 upload test",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("documents:upload"),
            {"title": "Knowledge Base", "file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.user, self.user)
        self.assertEqual(document.file_type, "txt")
        self.assertEqual(document.status, DocumentStatus.UPLOADED)
        mocked_delay.assert_called_once_with(document.id)

    def test_upload_rejects_unsupported_file_type(self):
        upload = SimpleUploadedFile(
            "malware.exe",
            b"fake-binary",
            content_type="application/octet-stream",
        )

        response = self.client.post(
            reverse("documents:upload"),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_list_only_returns_current_users_documents(self):
        my_document = Document.objects.create(
            user=self.user,
            title="Mine",
            file=SimpleUploadedFile("mine.txt", b"mine"),
            file_type="txt",
            status=DocumentStatus.READY,
            extracted_text="mine",
        )
        DocumentChunk.objects.create(
            document=my_document,
            chunk_index=0,
            text="mine",
            token_count=1,
        )
        Document.objects.create(
            user=self.other_user,
            title="Theirs",
            file=SimpleUploadedFile("theirs.txt", b"theirs"),
            file_type="txt",
        )

        response = self.client.get(reverse("documents:list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], my_document.id)
        self.assertEqual(response.data[0]["extracted_text_length"], 4)
        self.assertEqual(response.data[0]["chunk_count"], 1)

    def test_detail_and_delete_are_owner_scoped(self):
        document = Document.objects.create(
            user=self.user,
            title="Owner file",
            file=SimpleUploadedFile("owner.txt", b"owner"),
            file_type="txt",
        )
        other_document = Document.objects.create(
            user=self.other_user,
            title="Other file",
            file=SimpleUploadedFile("other.txt", b"other"),
            file_type="txt",
        )

        detail_response = self.client.get(
            reverse("documents:detail", kwargs={"pk": document.id})
        )
        forbidden_response = self.client.get(
            reverse("documents:detail", kwargs={"pk": other_document.id})
        )
        delete_response = self.client.delete(
            reverse("documents:detail", kwargs={"pk": document.id})
        )

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(forbidden_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=document.id).exists())

    def test_txt_extractor_reads_text(self):
        document = Document.objects.create(
            user=self.user,
            title="TXT file",
            file=SimpleUploadedFile("source.txt", b"Hello from Remzi text extraction"),
            file_type="txt",
            status=DocumentStatus.UPLOADED,
        )

        extracted_text = DocumentTextExtractor.extract(document=document)

        self.assertEqual(extracted_text, "Hello from Remzi text extraction")

    def test_docx_extractor_reads_paragraphs(self):
        document = Document.objects.create(
            user=self.user,
            title="DOCX file",
            file=make_uploaded_docx("Hello from a DOCX file"),
            file_type="docx",
            status=DocumentStatus.UPLOADED,
        )

        extracted_text = DocumentTextExtractor.extract(document=document)

        self.assertEqual(extracted_text, "Hello from a DOCX file")

    def test_process_document_task_marks_document_ready_with_chunks(self):
        document = Document.objects.create(
            user=self.user,
            title="Async file",
            file=SimpleUploadedFile("async.txt", b"Async extracted text"),
            file_type="txt",
            status=DocumentStatus.UPLOADED,
        )

        process_document_task(document.id)
        document.refresh_from_db()

        self.assertEqual(document.status, DocumentStatus.READY)
        self.assertEqual(document.extracted_text, "Async extracted text")
        self.assertEqual(document.error_message, "")
        self.assertEqual(document.chunks.count(), 1)
        self.assertEqual(document.chunks.first().text, "Async extracted text")

    def test_process_document_task_marks_empty_document_failed(self):
        document = Document.objects.create(
            user=self.user,
            title="Empty file",
            file=SimpleUploadedFile("empty.txt", b"   "),
            file_type="txt",
            status=DocumentStatus.UPLOADED,
        )

        process_document_task(document.id)
        document.refresh_from_db()

        self.assertEqual(document.status, DocumentStatus.FAILED)
        self.assertIn("No extractable text", document.error_message)
        self.assertEqual(document.chunks.count(), 0)

    def test_chunk_list_returns_chunks_for_owner(self):
        document = Document.objects.create(
            user=self.user,
            title="Chunked file",
            file=SimpleUploadedFile("chunked.txt", b"one two three"),
            file_type="txt",
            status=DocumentStatus.READY,
            extracted_text="one two three",
        )
        DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            text="one two three",
            token_count=3,
        )

        response = self.client.get(
            reverse("documents:chunks", kwargs={"document_id": document.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["chunk_index"], 0)
        self.assertEqual(response.data[0]["text"], "one two three")
        self.assertEqual(response.data[0]["token_count"], 3)

    def test_chunk_list_is_owner_scoped(self):
        other_document = Document.objects.create(
            user=self.other_user,
            title="Other chunked file",
            file=SimpleUploadedFile("other.txt", b"hidden"),
            file_type="txt",
            status=DocumentStatus.READY,
            extracted_text="hidden",
        )

        response = self.client.get(
            reverse("documents:chunks", kwargs={"document_id": other_document.id})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
