from django.contrib import admin

from .models import ChatMessage, ChatPresence


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "message_type", "created_at", "is_deleted")
    list_filter = ("message_type", "is_deleted", "created_at")
    search_fields = ("sender__email", "sender__first_name", "sender__last_name", "text")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChatPresence)
class ChatPresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "connected_at", "last_seen")
    list_filter = ("is_active", "connected_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
