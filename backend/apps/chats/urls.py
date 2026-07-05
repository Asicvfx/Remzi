from django.urls import path

from apps.chats.views import (
    ChatAskView,
    ChatAskStreamView,
    ChatMessageListView,
    ChatSessionDetailView,
    ChatSessionListCreateView,
)


app_name = "chats"

urlpatterns = [
    path("", ChatSessionListCreateView.as_view(), name="list_create"),
    path("<int:pk>/", ChatSessionDetailView.as_view(), name="detail"),
    path("<int:pk>/messages/", ChatMessageListView.as_view(), name="messages"),
    path("<int:pk>/ask/", ChatAskView.as_view(), name="ask"),
    path("<int:pk>/ask/stream/", ChatAskStreamView.as_view(), name="ask_stream"),
]
