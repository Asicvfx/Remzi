from django.db.models import Count

from apps.answers.services import AskQuestionService
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

        updates = []
        if session.title == "New chat":
            session.title = AskInChatService._title_from_question(payload["question"])
            updates.append("title")
        if not session.document_id and document:
            session.document = document
            updates.append("document")
        if updates:
            updates.append("updated_at")
            session.save(update_fields=updates)
        else:
            session.save(update_fields=["updated_at"])

        return session, message

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
