import json
import uuid
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.html import escape

from accounts.models import User
from chat.models import ChatMessage, ChatPresence, Conversation


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


class DirectChatConsumer(AsyncJsonWebsocketConsumer):
    """Authenticated per-user socket for private, membership-checked conversations."""

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_group_name = f"direct_chat_user_{self.user.pk}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        await self.set_presence(True)
        await self.broadcast_presence(True)
        await self.send_json({"type": "connected", "user_id": self.user.pk})

    async def disconnect(self, close_code):
        if not hasattr(self, "user_group_name"):
            return
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        await self.set_presence(False)
        await self.broadcast_presence(False)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except (json.JSONDecodeError, TypeError):
            await self.send_json({"type": "error", "message": "Xabar formati noto‘g‘ri."})
            return

        action = payload.get("type")
        try:
            conversation_id = int(payload.get("conversation_id"))
        except (TypeError, ValueError):
            await self.send_json({"type": "error", "message": "Suhbat topilmadi."})
            return

        if action == "message":
            text = (payload.get("text") or "").strip()
            if not text:
                await self.send_json({"type": "error", "message": "Bo‘sh xabar yuborib bo‘lmaydi."})
                return
            if len(text) > 4000:
                await self.send_json({"type": "error", "message": "Xabar juda uzun."})
                return
            result = await self.persist_direct_message(
                conversation_id, text, payload.get("client_id")
            )
            if not result.get("ok"):
                await self.send_json({"type": "error", "message": result["error"]})
                return
            await self.broadcast_to_participants(conversation_id, {
                "type": "new_message",
                "conversation_id": conversation_id,
                "message": result["message"],
            })
            return

        if action == "typing":
            result = await self.get_other_participant(conversation_id)
            if not result:
                await self.send_json({"type": "error", "message": "Suhbatga ruxsat yo‘q."})
                return
            await self.channel_layer.group_send(
                f"direct_chat_user_{result['id']}",
                {"type": "direct_event", "event": {
                    "type": "typing",
                    "conversation_id": conversation_id,
                    "user_id": self.user.pk,
                    "username": self.user.get_full_name() or "Foydalanuvchi",
                    "is_typing": bool(payload.get("is_typing")),
                }},
            )
            return

        if action == "delivered":
            receipt = await self.mark_delivered(conversation_id, payload.get("message_id"))
            if receipt:
                await self.channel_layer.group_send(
                    f"direct_chat_user_{receipt['sender_id']}",
                    {"type": "direct_event", "event": receipt},
                )
            return

        if action == "read":
            receipt = await self.mark_read(conversation_id)
            if not receipt:
                await self.send_json({"type": "error", "message": "Suhbatga ruxsat yo‘q."})
                return
            await self.broadcast_to_participants(conversation_id, receipt)

    async def direct_event(self, event):
        await self.send_json(event["event"])

    async def broadcast_to_participants(self, conversation_id, event):
        participant_ids = await self.get_participant_ids(conversation_id)
        for participant_id in participant_ids:
            await self.channel_layer.group_send(
                f"direct_chat_user_{participant_id}",
                {"type": "direct_event", "event": event},
            )

    @database_sync_to_async
    def get_participant_ids(self, conversation_id):
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return []
        if not conversation.includes(self.user):
            return []
        return [conversation.participant_one_id, conversation.participant_two_id]

    @database_sync_to_async
    def get_other_participant(self, conversation_id):
        try:
            conversation = Conversation.objects.select_related(
                "participant_one", "participant_two"
            ).get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return None
        if not conversation.includes(self.user):
            return None
        other = conversation.other_participant(self.user)
        return {"id": other.pk} if other else None

    @database_sync_to_async
    def persist_direct_message(self, conversation_id, text, client_id):
        try:
            conversation = Conversation.objects.select_related(
                "participant_one", "participant_two"
            ).get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return {"ok": False, "error": "Suhbat topilmadi."}
        if not conversation.includes(self.user):
            return {"ok": False, "error": "Suhbatga ruxsat yo‘q."}

        parsed_client_id = None
        if client_id:
            try:
                parsed_client_id = uuid.UUID(str(client_id))
            except (ValueError, TypeError, AttributeError):
                return {"ok": False, "error": "Xabar identifikatori noto‘g‘ri."}

        try:
            with transaction.atomic():
                if parsed_client_id:
                    existing = ChatMessage.objects.filter(client_id=parsed_client_id).select_related("sender").first()
                    if existing:
                        if existing.sender_id != self.user.pk or existing.conversation_id != conversation.pk:
                            return {"ok": False, "error": "Xabar identifikatori band."}
                        message = existing
                    else:
                        message = ChatMessage.objects.create(
                            sender=self.user,
                            conversation=conversation,
                            client_id=parsed_client_id,
                            text=text,
                            message_type=ChatMessage.MESSAGE_TYPE_TEXT,
                            status=ChatMessage.STATUS_SENT,
                        )
                else:
                    message = ChatMessage.objects.create(
                        sender=self.user,
                        conversation=conversation,
                        text=text,
                        message_type=ChatMessage.MESSAGE_TYPE_TEXT,
                        status=ChatMessage.STATUS_SENT,
                    )
                conversation.updated_at = message.created_at
                conversation.save(update_fields=["updated_at"])
        except IntegrityError:
            if not parsed_client_id:
                raise
            message = ChatMessage.objects.select_related("sender").get(client_id=parsed_client_id)
            if message.sender_id != self.user.pk or message.conversation_id != conversation.pk:
                return {"ok": False, "error": "Xabar identifikatori band."}

        message = ChatMessage.objects.select_related("sender").get(pk=message.pk)
        return {"ok": True, "message": self.serialize_direct_message(message)}

    def serialize_direct_message(self, message):
        return {
            "id": message.pk,
            "client_id": str(message.client_id) if message.client_id else None,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender.get_full_name() or "Foydalanuvchi",
            "sender_avatar": message.sender.profile_photo_url,
            "text": message.text,
            "message_type": message.message_type,
            "status": message.status,
            "created_at": message.created_at.isoformat(),
            "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
            "read_at": message.read_at.isoformat() if message.read_at else None,
            "is_mine": message.sender_id == self.user.pk,
        }

    @database_sync_to_async
    def mark_delivered(self, conversation_id, message_id):
        try:
            message = ChatMessage.objects.select_related("conversation").get(
                pk=message_id,
                conversation_id=conversation_id,
                is_deleted=False,
            )
        except (ChatMessage.DoesNotExist, TypeError, ValueError):
            return None
        if not message.conversation.includes(self.user) or message.sender_id == self.user.pk:
            return None
        if message.status == ChatMessage.STATUS_SENT:
            message.status = ChatMessage.STATUS_DELIVERED
            message.delivered_at = timezone.now()
            message.save(update_fields=["status", "delivered_at", "updated_at"])
        return {
            "type": "receipt_update",
            "conversation_id": conversation_id,
            "message_ids": [message.pk],
            "status": message.status,
            "sender_id": message.sender_id,
        }

    @database_sync_to_async
    def mark_read(self, conversation_id):
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return None
        if not conversation.includes(self.user):
            return None
        now = timezone.now()
        incoming = ChatMessage.objects.filter(
            conversation=conversation,
            is_deleted=False,
            read_at__isnull=True,
        ).exclude(sender_id=self.user.pk)
        message_ids = list(incoming.values_list("pk", flat=True))
        incoming.update(status=ChatMessage.STATUS_READ, read_at=now)
        if self.user.pk == conversation.participant_one_id:
            conversation.participant_one_read_at = now
            sender_id = conversation.participant_two_id
        else:
            conversation.participant_two_read_at = now
            sender_id = conversation.participant_one_id
        conversation.save(update_fields=["participant_one_read_at", "participant_two_read_at"])
        return {
            "type": "receipt_update",
            "conversation_id": conversation_id,
            "message_ids": message_ids,
            "status": ChatMessage.STATUS_READ,
            "read_by": self.user.pk,
            "sender_id": sender_id,
            "unread_count": 0,
        }

    @database_sync_to_async
    def set_presence(self, is_online):
        presence, _ = ChatPresence.objects.get_or_create(user=self.user)
        presence.is_active = is_online
        presence.last_seen = timezone.now()
        if is_online:
            presence.connected_at = timezone.now()
        presence.save(update_fields=["is_active", "last_seen", "connected_at", "updated_at"])

    async def broadcast_presence(self, is_online):
        participant_ids = await self.get_related_participant_ids()
        event = {
            "type": "presence_update",
            "user_id": self.user.pk,
            "is_online": is_online,
        }
        for participant_id in participant_ids:
            await self.channel_layer.group_send(
                f"direct_chat_user_{participant_id}",
                {"type": "direct_event", "event": event},
            )

    @database_sync_to_async
    def get_related_participant_ids(self):
        ids = set(Conversation.objects.filter(
            participant_one_id=self.user.pk
        ).values_list("participant_two_id", flat=True))
        ids.update(Conversation.objects.filter(
            participant_two_id=self.user.pk
        ).values_list("participant_one_id", flat=True))
        return ids
