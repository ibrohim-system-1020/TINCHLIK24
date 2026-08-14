from django.test import TestCase

from django.contrib.auth import get_user_model

from bots.admin.utils import is_admin_telegram_id

User = get_user_model()


class AdminAccessTests(TestCase):
    def test_telegram_admin_whitelist_includes_target_user(self):
        self.assertIn(8461653028, is_admin_telegram_id.__globals__.get("settings").ADMIN_TELEGRAM_IDS)

    def test_admin_user_has_access_flag_and_profile_context(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPassword123",
            telegram_id=8461653028,
            telegram_username="admin_user",
            first_name="Admin",
            last_name="User",
        )

        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

        self.client.force_login(user)
        response = self.client.get("/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_admin"])
        self.assertContains(response, "Admin boshqaruvi")
