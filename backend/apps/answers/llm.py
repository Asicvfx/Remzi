from dataclasses import dataclass

from django.conf import settings


SYSTEM_PROMPT = """You are Remzi, a careful RAG assistant.
Answer only from the provided citations.
If the citations do not contain enough information, say that the documents do not contain enough information.
Keep the answer concise and practical.
Answer in the same language as the user's question.
Mention citation chunk IDs when useful, but do not invent facts."""


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    model: str


class OpenAIAnswerClient:
    """Thin adapter around OpenAI so the rest of the app stays provider-neutral."""

    def __init__(
        self,
        api_key=None,
        model=None,
        enabled=None,
        timeout_seconds=None,
    ):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL
        self.enabled = (
            enabled if enabled is not None else settings.OPENAI_ANSWER_ENABLED
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.OPENAI_TIMEOUT_SECONDS
        )

    def generate_answer(self, question, citations):
        if not self.enabled or not self.api_key or not citations:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        prompt = self._build_user_prompt(question=question, citations=citations)

        try:
            client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "developer", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception:
            return None

        answer = getattr(response, "output_text", "").strip()
        if not answer:
            return None

        return GeneratedAnswer(answer=answer, model=self.model)

    def stream_answer_chunks(self, question, citations):
        if not self.enabled or not self.api_key or not citations:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            return None

        prompt = self._build_user_prompt(question=question, citations=citations)

        def chunk_iterator():
            client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
            with client.responses.stream(
                model=self.model,
                input=[
                    {"role": "developer", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            ) as stream:
                for event in stream:
                    if getattr(event, "type", "") == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        if delta:
                            yield delta

        return chunk_iterator()

    @staticmethod
    def _build_user_prompt(question, citations):
        citation_blocks = []
        for citation in citations:
            citation_blocks.append(
                "\n".join(
                    [
                        f"Document ID: {citation['document_id']}",
                        f"Document title: {citation['document_title']}",
                        f"Chunk ID: {citation['chunk_id']}",
                        f"Chunk index: {citation['chunk_index']}",
                        f"Text: {citation['text']}",
                    ]
                )
            )

        return "\n\n".join(
            [
                f"Question: {question}",
                "Citations:",
                "\n\n---\n\n".join(citation_blocks),
            ]
        )
