from django.db import transaction

from apps.documents.models import Document, DocumentStatus


class CreateDocumentService:
    @staticmethod
    def execute(*, user, validated_data):
        document = Document.objects.create(user=user, **validated_data)

        def enqueue_processing():
            from apps.documents.tasks import process_document_task

            process_document_task.delay(document.id)

        transaction.on_commit(enqueue_processing)
        return document


class DocumentProcessingService:
    @staticmethod
    def mark_processing(*, document):
        document.status = DocumentStatus.PROCESSING
        document.error_message = ""
        document.save(update_fields=("status", "error_message", "updated_at"))
        return document

    @staticmethod
    def mark_ready(*, document, extracted_text):
        document.status = DocumentStatus.READY
        document.extracted_text = extracted_text
        document.error_message = ""
        document.save(
            update_fields=("status", "extracted_text", "error_message", "updated_at")
        )
        return document

    @staticmethod
    def mark_failed(*, document, error_message):
        document.status = DocumentStatus.FAILED
        document.error_message = error_message
        document.save(update_fields=("status", "error_message", "updated_at"))
        return document
