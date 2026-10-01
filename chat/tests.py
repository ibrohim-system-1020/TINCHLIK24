import json
import uuid

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from channels.testing import WebsocketCommunicator

from chat.models import ChatMessage, Conversation


class ChatSendMessageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="chatuser",
        )

    def test_anonymous_user_cannot_send_message(self):
        response = self.client.post(
            reverse("chat:send_message"),
            data=json.dumps({"message": "Salom"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, {302, 403})

    def test_chat_page_exposes_real_current_user_id_for_owner_checks(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("chat:chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chatRoot"')
        self.assertContains(response, f'data-current-user-id="{self.user.id}"')

    def test_history_payload_uses_sender_id_for_per_user_ownership(self):
        other = get_user_model().objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            username="otheruser",
        )
        message = ChatMessage.objects.create(sender=other, text="Not mine")

        self.client.force_login(self.user)
        response = self.client.get(reverse("chat:history"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["messages"][0]["sender_id"], other.id)
        self.assertFalse(payload["messages"][0]["is_mine"])
        self.assertEqual(payload["messages"][0]["can_delete"], False)
        self.assertEqual(message.text, "Not mine")

    def test_authenticated_user_can_send_message(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("chat:send_message"),
            data=json.dumps({"message": "Salom"}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.get().text, "Salom")

    def test_empty_message_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("chat:send_message"),
            data=json.dumps({"message": "   "}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["error"].lower())

    def test_user_can_delete_own_message_within_15_minutes(self):
        self.client.force_login(self.user)
        message = ChatMessage.objects.create(sender=self.user, text="Delete me")

        response = self.client.post(
            reverse("chat:delete_message", args=[message.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)

    def test_user_cannot_delete_other_users_message(self):
        other = get_user_model().objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
            username="otheruser",
        )
        message = ChatMessage.objects.create(sender=other, text="Not mine")

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("chat:delete_message", args=[message.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 403)
        message.refresh_from_db()
        self.assertFalse(message.is_deleted)


class DirectConversationApiTests(TestCase):
    def setUp(self):
        self.user_a = get_user_model().objects.create_user(
            email="direct-a@example.test", password="StrongPassword123", first_name="User", last_name="A"
        )
        self.user_b = get_user_model().objects.create_user(
            email="direct-b@example.test", password="StrongPassword123", first_name="User", last_name="B"
        )
        self.user_c = get_user_model().objects.create_user(
            email="direct-c@example.test", password="StrongPassword123", first_name="User", last_name="C"
        )
        self.conversation, _ = Conversation.get_or_create_direct(self.user_a, self.user_b)

    def test_only_conversation_members_can_load_history(self):
        ChatMessage.objects.create(
            sender=self.user_a,
            conversation=self.conversation,
            text="Private hello",
        )

        self.client.force_login(self.user_b)
        response = self.client.get(reverse("chat:history"), {"conversation": self.conversation.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"][0]["text"], "Private hello")

        self.client.force_login(self.user_c)
        denied = self.client.get(reverse("chat:history"), {"conversation": self.conversation.pk})
        self.assertEqual(denied.status_code, 403)

    def test_conversation_start_reuses_pair_and_excludes_self(self):
        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse("chat:start_conversation"),
            data=json.dumps({"user_id": self.user_b.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["conversation_id"], self.conversation.pk)

        self_response = self.client.post(
            reverse("chat:start_conversation"),
            data=json.dumps({"user_id": self.user_a.pk}),
            content_type="application/json",
        )
        self.assertEqual(self_response.status_code, 400)
        self.assertEqual(Conversation.objects.count(), 1)


class DirectConversationWebSocketTests(TransactionTestCase):
    def test_message_is_realtime_saved_and_read_status_persists(self):
        user_model = get_user_model()
        user_a = user_model.objects.create_user(
            email="ws-a@example.test", password="StrongPassword123", first_name="Socket", last_name="A"
        )
        user_b = user_model.objects.create_user(
            email="ws-b@example.test", password="StrongPassword123", first_name="Socket", last_name="B"
        )
        conversation, _ = Conversation.get_or_create_direct(user_a, user_b)

        client_a = Client()
        client_a.force_login(user_a)
        client_b = Client()
        client_b.force_login(user_b)
        cookie_name = "sessionid"
        headers_a = [(b"cookie", f"{cookie_name}={client_a.cookies[cookie_name].value}".encode())]
        headers_b = [(b"cookie", f"{cookie_name}={client_b.cookies[cookie_name].value}".encode())]

        async def receive_type(socket, expected_type, expected_status=None):
            for _ in range(10):
                event = await socket.receive_json_from(timeout=3)
                if event.get("type") == expected_type and (
                    expected_status is None or event.get("status") == expected_status
                ):
                    return event
            raise AssertionError(f"WebSocket event {expected_type!r} not received")

        async def exchange_messages():
            from config.asgi import application

            socket_a = WebsocketCommunicator(application, "/ws/chat/direct/", headers=headers_a)
            socket_b = WebsocketCommunicator(application, "/ws/chat/direct/", headers=headers_b)
            connected_a, _ = await socket_a.connect()
            connected_b, _ = await socket_b.connect()
            self.assertTrue(connected_a)
            self.assertTrue(connected_b)
            await receive_type(socket_a, "connected")
            await receive_type(socket_b, "connected")

            client_id = str(uuid.uuid4())
            await socket_a.send_json_to({
                "type": "message",
                "conversation_id": conversation.pk,
                "client_id": client_id,
                "text": "Salom realtime",
            })
            incoming = await receive_type(socket_b, "new_message")
            self.assertEqual(incoming["message"]["text"], "Salom realtime")
            self.assertEqual(incoming["message"]["client_id"], client_id)

            await socket_b.send_json_to({
                "type": "delivered",
                "conversation_id": conversation.pk,
                "message_id": incoming["message"]["id"],
            })
            await receive_type(socket_a, "receipt_update", "delivered")
            await socket_b.send_json_to({"type": "read", "conversation_id": conversation.pk})
            await receive_type(socket_a, "receipt_update", "read")

            await socket_a.disconnect()
            await socket_b.disconnect()

        async_to_sync(exchange_messages)()

        message = ChatMessage.objects.get(client_id=uuid.UUID(client_id))
        self.assertEqual(message.conversation_id, conversation.pk)
        self.assertEqual(message.status, ChatMessage.STATUS_READ)
        self.assertIsNotNone(message.read_at)

        history = client_b.get(reverse("chat:history"), {"conversation": conversation.pk})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["messages"][0]["text"], "Salom realtime")
        self.assertEqual(ChatMessage.objects.filter(conversation=conversation).count(), 1)
