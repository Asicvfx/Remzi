from celery import shared_task

from apps.chunks.services import CreateDocumentChunksService
from apps.documents.extractors import DocumentTextExtractor
from apps.documents.models import Document
from apps.documents.services import DocumentProcessingService


@shared_task(bind=True, ignore_result=True)
def process_document_task(self, document_id):
    document = Document.objects.get(id=document_id)
    DocumentProcessingService.mark_processing(document=document)

    try:
        extracted_text = DocumentTextExtractor.extract(document=document)
        CreateDocumentChunksService.execute(document=document, text=extracted_text)
    except Exception as exc:
        DocumentProcessingService.mark_failed(document=document, error_message=str(exc))
        return

    DocumentProcessingService.mark_ready(document=document, extracted_text=extracted_text)
