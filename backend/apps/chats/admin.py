from django.contrib import admin

from apps.chats.models import ChatMessage, ChatSession


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("question", "answer", "answer_mode", "model", "created_at")
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "document", "updated_at", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    inlines = (ChatMessageInline,)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "answer_mode", "model", "created_at")
    list_filter = ("answer_mode", "created_at")
    search_fields = ("question", "answer", "session__title")
