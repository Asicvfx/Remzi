from django.utils import timezone

from apps.chunks.models import DocumentChunk
from apps.search.embeddings import LocalHashingEmbeddingProvider


DEFAULT_CHUNK_TOKEN_LIMIT = 200
DEFAULT_CHUNK_OVERLAP = 40


class TextChunker:
    def __init__(
        self,
        max_tokens=DEFAULT_CHUNK_TOKEN_LIMIT,
        overlap_tokens=DEFAULT_CHUNK_OVERLAP,
    ):
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        if overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative")
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, text):
        words = (text or "").split()
        if not words:
            return []

        chunks = []
        start = 0
        step = self.max_tokens - self.overlap_tokens

        while start < len(words):
            end = start + self.max_tokens
            chunks.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start += step

        return chunks


class CreateDocumentChunksService:
    @staticmethod
    def execute(document, text):
        DocumentChunk.objects.filter(document=document).delete()

        provider = LocalHashingEmbeddingProvider()
        embedded_at = timezone.now()
        chunks = TextChunker().split(text)
        chunk_objects = [
            DocumentChunk(
                document=document,
                chunk_index=index,
                text=chunk_text,
                token_count=len(chunk_text.split()),
                embedding=provider.embed(chunk_text),
                embedding_model=provider.model_name,
                embedded_at=embedded_at,
            )
            for index, chunk_text in enumerate(chunks)
        ]

        return DocumentChunk.objects.bulk_create(chunk_objects)
