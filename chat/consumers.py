import json
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.html import escape

from accounts.models import User
from chat.models import ChatMessage, ChatPresence


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=403)
            return

        self.room_group_name = "global_chat"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send_presence_snapshot()
        await self.notify_presence(online=True)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.notify_presence(online=False)

    async def receive(self, text_data=None, bytes_data=None):
        if not self.scope["user"].is_authenticated:
            await self.send(json.dumps({"type": "error", "message": "Authentication required."}))
            return

        user = self.scope["user"]

        try:
            payload = json.loads(text_data or "{}") if text_data else {}
        except json.JSONDecodeError:
            await self.send(json.dumps({"type": "error", "message": "Invalid message format."}))
            return

        action = payload.get("type")

        if action == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_event",
                    "user_id": user.id,
                    "username": user.get_full_name() or user.email,
                    "is_typing": payload.get("is_typing", False),
                },
            )
            return

        if action == "message":
            text = (payload.get("text") or "").strip()
            if not text:
                await self.send(json.dumps({"type": "error", "message": "Message cannot be empty."}))
                return
            if len(text) > 2000:
                await self.send(json.dumps({"type": "error", "message": "Message too long."}))
                return

            message = await self.create_text_message(user, text, payload.get("reply_to"))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message_event",
                    "message": await self.serialize_message(message),
                },
            )
            return

        if action == "delete_message":
            message_id = payload.get("message_id")
            if not message_id:
                return
            message = await self.get_message_for_admin(message_id)
            if message is None:
                await self.send(json.dumps({"type": "error", "message": "Message not found."}))
                return
            is_admin = await self.user_is_admin(user)
            if not is_admin:
                await self.send(json.dumps({"type": "error", "message": "Permission denied."}))
                return
            await self.delete_message(message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "delete_message_event",
                    "message_id": message_id,
                },
            )
            return

    async def chat_message_event(self, event):
        await self.send(text_data=json.dumps({"type": "new_message", "message": event["message"]}))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({"type": "typing", "user_id": event["user_id"], "username": event["username"], "is_typing": event["is_typing"]}))

    async def delete_message_event(self, event):
        await self.send(text_data=json.dumps({"type": "delete_message", "message_id": event["message_id"]}))

    async def send_presence_snapshot(self):
        online_users = await self.get_online_users()
        await self.send(json.dumps({"type": "presence", "online_count": len(online_users), "users": online_users}))

    async def notify_presence(self, online: bool):
        await self.update_presence(self.scope["user"], online)
        online_users = await self.get_online_users()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "presence_event",
                "online_count": len(online_users),
                "users": online_users,
            },
        )

    async def presence_event(self, event):
        await self.send(json.dumps({"type": "presence", "online_count": event["online_count"], "users": event["users"]}))

    @database_sync_to_async
    def get_online_users(self):
        users = []
        for presence in ChatPresence.objects.filter(is_active=True, last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)):
            user = presence.user
            users.append({
                "id": user.id,
                "name": user.get_full_name() or user.email,
                "email": user.email,
                "avatar": user.profile_photo_url,
            })
        return users

    @database_sync_to_async
    def update_presence(self, user, is_online):
        presence, _ = ChatPresence.objects.get_or_create(user=user)
        presence.is_active = is_online
        presence.last_seen = timezone.now()
        if is_online:
            presence.connected_at = timezone.now()
        presence.save(update_fields=["is_active", "last_seen", "connected_at", "updated_at"])

    @database_sync_to_async
    def user_is_admin(self, user):
        return bool(getattr(user, "is_admin", False) or getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))

    @database_sync_to_async
    def create_text_message(self, user, text, reply_to_id):
        reply_to = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id)
            except ChatMessage.DoesNotExist:
                reply_to = None

        message = ChatMessage.objects.create(
            sender=user,
            text=text,
            message_type=ChatMessage.MESSAGE_TYPE_TEXT,
            reply_to=reply_to,
        )
        return message

    @database_sync_to_async
    def delete_message(self, message):
        message.is_deleted = True
        message.text = "[Deleted by admin]"
        message.save(update_fields=["is_deleted", "text", "updated_at"])

    @database_sync_to_async
    def get_message_for_admin(self, message_id):
        try:
            return ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        user = self.scope["user"]
        is_mine = message.sender_id == user.id
        can_delete = is_mine and not message.is_deleted and timezone.now() <= message.created_at + timezone.timedelta(minutes=15)
        payload = {
            "id": message.id,
            "sender_id": message.sender_id,
            "sender_name": message.sender.get_full_name() or message.sender.email,
            "sender_email": message.sender.email,
            "sender_avatar": message.sender.profile_photo_url,
            "text": escape(message.text),
            "message_type": message.message_type,
            "created_at": message.created_at.isoformat(),
            "reply_to": None,
            "is_mine": is_mine,
            "can_delete": can_delete,
        }
        if message.reply_to_id:
            payload["reply_to"] = {
                "id": message.reply_to_id,
                "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
                "text": escape(message.reply_to.text or ""),
            }
        return payload
