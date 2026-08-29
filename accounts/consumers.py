import json

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from accounts.models import PendingRegistration


class RegistrationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.public_id = self.scope["url_route"]["kwargs"].get("public_id")
        if not self.public_id:
            await self.close(code=4004)
            return

        pending = await self.get_pending(self.public_id)
        if pending is None:
            await self.close(code=4004)
            return

        session_key = self.scope.get("session", {}).session_key if self.scope.get("session") else None
        if not session_key or pending.session_key != session_key:
            await self.close(code=403)
            return

        self.room_group_name = f"registration_{self.public_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        status = pending.status
        await self.send(text_data=json.dumps({
            "type": "registration.status",
            "status": status,
            "verified": pending.is_verified,
            "completed": pending.is_completed,
            "expired": pending.is_expired(),
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            await self.send(text_data=json.dumps({"type": "registration.pong"}))

    @database_sync_to_async
    def get_pending(self, public_id):
        try:
            return PendingRegistration.objects.get(public_id=public_id)
        except PendingRegistration.DoesNotExist:
            return None
