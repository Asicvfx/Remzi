from apps.chunks.models import DocumentChunk
from apps.common.text import repair_mojibake
from apps.search.embeddings import LocalHashingEmbeddingProvider, cosine_similarity


SEARCH_TEXT_PREVIEW_LENGTH = 1200


class SearchChunksService:
    @staticmethod
    def execute(user, query, limit=5, document_id=None):
        provider = LocalHashingEmbeddingProvider()
        query_variants = list(dict.fromkeys([query, repair_mojibake(query)]))
        query_embeddings = [provider.embed(query_variant) for query_variant in query_variants]

        chunks = DocumentChunk.objects.filter(document__user=user).exclude(embedding=[])
        if document_id is not None:
            chunks = chunks.filter(document_id=document_id)

        chunks = chunks.select_related("document").only(
            "id",
            "document_id",
            "chunk_index",
            "embedding",
            "document__id",
            "document__title",
        )

        scored_results = []
        for chunk in chunks.iterator(chunk_size=200):
            score = max(
                cosine_similarity(query_embedding, chunk.embedding)
                for query_embedding in query_embeddings
            )
            if score <= 0:
                continue
            scored_results.append((score, chunk.id))

        scored_results.sort(key=lambda item: item[0], reverse=True)
        top_results = scored_results[:limit]
        chunk_ids = [chunk_id for _, chunk_id in top_results]
        chunks_by_id = {
            chunk.id: chunk
            for chunk in DocumentChunk.objects.filter(id__in=chunk_ids)
            .select_related("document")
            .only("id", "document_id", "chunk_index", "text", "document__id", "document__title")
        }

        results = []
        for score, chunk_id in top_results:
            chunk = chunks_by_id[chunk_id]
            text = repair_mojibake(chunk.text)
            results.append(
                {
                    "document_id": chunk.document_id,
                    "document_title": repair_mojibake(chunk.document.title),
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "score": round(score, 6),
                    "text": text[:SEARCH_TEXT_PREVIEW_LENGTH],
                }
            )

        return results
