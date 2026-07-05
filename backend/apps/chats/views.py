import json

from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status, views
from rest_framework.response import Response

from apps.chats.models import ChatMessage, ChatSession
from apps.chats.serializers import (
    ChatAskRequestSerializer,
    ChatAskResponseSerializer,
    ChatMessageSerializer,
    ChatSessionCreateSerializer,
    ChatSessionSerializer,
)
from apps.chats.services import (
    AskInChatService,
    AskInChatStreamService,
    CreateChatSessionService,
    chat_session_queryset,
)


def _sse_event(event, data):
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@extend_schema_view(
    get=extend_schema(
        summary="List chat sessions",
        description="Returns chat sessions owned by the authenticated user.",
        responses={200: ChatSessionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Create a chat session",
        description="Creates an empty chat session for the authenticated user.",
        request=ChatSessionCreateSerializer,
        responses={201: ChatSessionSerializer},
    ),
)
class ChatSessionListCreateView(generics.GenericAPIView):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChatSessionCreateSerializer
        return ChatSessionSerializer

    def get(self, request):
        sessions = chat_session_queryset(request.user)
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ChatSessionCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        session = CreateChatSessionService.execute(
            user=request.user,
            title=serializer.validated_data.get("title", ""),
            document_id=serializer.validated_data.get("document_id"),
        )
        response_serializer = ChatSessionSerializer(
            chat_session_queryset(request.user).get(id=session.id)
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Get chat session",
        description="Returns one chat session owned by the authenticated user.",
    ),
    delete=extend_schema(
        summary="Delete chat session",
        description="Deletes one chat session owned by the authenticated user.",
    ),
)
class ChatSessionDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        return chat_session_queryset(self.request.user)


@extend_schema(
    summary="List chat messages",
    description="Returns messages for one chat session owned by the authenticated user.",
    responses={200: ChatMessageSerializer(many=True)},
)
class ChatMessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        return ChatMessage.objects.filter(
            session_id=self.kwargs["pk"],
            session__user=self.request.user,
        ).select_related("document", "session")


@extend_schema(
    summary="Ask inside a chat session",
    description="Runs the RAG ask pipeline, stores the question and answer, and returns the saved message.",
    request=ChatAskRequestSerializer,
    responses={200: ChatAskResponseSerializer},
)
class ChatAskView(views.APIView):
    def post(self, request, pk):
        session = generics.get_object_or_404(
            ChatSession.objects.filter(user=request.user),
            pk=pk,
        )
        serializer = ChatAskRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        session, message = AskInChatService.execute(
            user=request.user,
            session=session,
            question=serializer.validated_data["question"],
            limit=serializer.validated_data["limit"],
            document_id=serializer.validated_data.get("document_id"),
        )
        session = chat_session_queryset(request.user).get(id=session.id)
        payload = {"session": session, "message": message}
        response_serializer = ChatAskResponseSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Stream ask inside a chat session",
    description="Runs the RAG ask pipeline and streams answer deltas before returning the saved chat message.",
    request=ChatAskRequestSerializer,
    responses={200: ChatAskResponseSerializer},
)
class ChatAskStreamView(views.APIView):
    def post(self, request, pk):
        session = generics.get_object_or_404(
            ChatSession.objects.filter(user=request.user),
            pk=pk,
        )
        serializer = ChatAskRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        def event_stream():
            try:
                for event, payload in AskInChatStreamService.execute(
                    user=request.user,
                    session=session,
                    question=serializer.validated_data["question"],
                    limit=serializer.validated_data["limit"],
                    document_id=serializer.validated_data.get("document_id"),
                ):
                    if event == "done":
                        streamed_session = chat_session_queryset(request.user).get(
                            id=payload["session"].id
                        )
                        response_serializer = ChatAskResponseSerializer(
                            {
                                "session": streamed_session,
                                "message": payload["message"],
                            }
                        )
                        yield _sse_event("done", response_serializer.data)
                    else:
                        yield _sse_event(event, payload)
            except Exception as exc:
                yield _sse_event("error", {"detail": str(exc)})

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        return response