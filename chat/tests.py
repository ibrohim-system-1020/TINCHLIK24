import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chat.models import ChatMessage


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
