from django.db.models import Count

from apps.answers.llm import OpenAIAnswerClient
from apps.answers.services import AskQuestionService, LocalExtractiveAnswerComposer
from apps.chats.models import ChatMessage, ChatSession
from apps.documents.models import Document


class CreateChatSessionService:
    @staticmethod
    def execute(user, title="", document_id=None):
        document = None
        if document_id:
            document = Document.objects.get(id=document_id, user=user)

        if not title and document:
            title = f"Chat: {document.title}"
        if not title:
            title = "New chat"

        return ChatSession.objects.create(
            user=user,
            title=title,
            document=document,
        )



class AskInChatStreamService:
    @staticmethod
    def execute(user, session, question, limit=5, document_id=None):
        if session.user_id != user.id:
            raise ChatSession.DoesNotExist

        effective_document_id = document_id
        if effective_document_id is None and session.document_id:
            effective_document_id = session.document_id

        context = AskQuestionService.build_context(
            user=user,
            question=question,
            limit=limit,
            document_id=effective_document_id,
        )

        document = None
        if context["document_id"]:
            document = Document.objects.get(id=context["document_id"], user=user)

        yield "metadata", {
            "question": context["question"],
            "document_id": context["document_id"],
            "citations": context["citations"],
        }

        answer_chunks = []
        answer_mode = "local"
        model = ""
        openai_client = OpenAIAnswerClient()
        chunk_stream = openai_client.stream_answer_chunks(
            question=context["question"],
            citations=context["citations"],
        )

        if chunk_stream is not None:
            try:
                for delta in chunk_stream:
                    answer_chunks.append(delta)
                    answer_mode = "openai"
                    model = openai_client.model
                    yield "answer_delta", {"delta": delta}
            except Exception:
                answer_chunks = []
                answer_mode = "local"
                model = ""

        if not answer_chunks:
            local_answer = LocalExtractiveAnswerComposer.compose(
                question=context["question"],
                search_results=context["search_results"],
            )
            for delta in AskInChatStreamService._chunk_text(local_answer):
                answer_chunks.append(delta)
                yield "answer_delta", {"delta": delta}

        answer = "".join(answer_chunks)
        message = ChatMessage.objects.create(
            session=session,
            question=context["question"],
            answer=answer,
            answer_mode=answer_mode,
            model=model,
            document=document,
            citations=context["citations"],
        )

        AskInChatService.update_session_after_message(
            session=session,
            question=context["question"],
            document=document,
        )
        yield "done", {"session": session, "message": message}

    @staticmethod
    def _chunk_text(text, chunk_size=28):
        for index in range(0, len(text), chunk_size):
            yield text[index : index + chunk_size]

class AskInChatService:
    @staticmethod
    def execute(user, session, question, limit=5, document_id=None):
        if session.user_id != user.id:
            raise ChatSession.DoesNotExist

        effective_document_id = document_id
        if effective_document_id is None and session.document_id:
            effective_document_id = session.document_id

        payload = AskQuestionService.execute(
            user=user,
            question=question,
            limit=limit,
            document_id=effective_document_id,
        )

        document = None
        if payload["document_id"]:
            document = Document.objects.get(id=payload["document_id"], user=user)

        message = ChatMessage.objects.create(
            session=session,
            question=payload["question"],
            answer=payload["answer"],
            answer_mode=payload["answer_mode"],
            model=payload["model"],
            document=document,
            citations=payload["citations"],
        )

        AskInChatService.update_session_after_message(
            session=session,
            question=payload["question"],
            document=document,
        )

        return session, message

    @staticmethod
    def update_session_after_message(session, question, document=None):
        updates = []
        if session.title == "New chat":
            session.title = AskInChatService._title_from_question(question)
            updates.append("title")
        if not session.document_id and document:
            session.document = document
            updates.append("document")
        if updates:
            updates.append("updated_at")
            session.save(update_fields=updates)
        else:
            session.save(update_fields=["updated_at"])

    @staticmethod
    def _title_from_question(question):
        words = " ".join(question.split())
        if len(words) <= 60:
            return words
        return words[:57].rstrip() + "..."


def chat_session_queryset(user):
    return (
        ChatSession.objects.filter(user=user)
        .select_related("document")
        .annotate(message_count=Count("messages"))
    )
