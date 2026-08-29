from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.forms import normalize_phone
from accounts.models import PendingRegistration

User = get_user_model()


class AdminAccessTests(TestCase):
    def test_admin_phone_is_the_only_admin_phone(self):
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPassword123",
            first_name="Admin",
            last_name="User",
            telefon="+998 99 164 98 48",
        )

        self.assertEqual(normalize_phone(admin_user.telefon), "+998991649848")
        self.assertTrue(admin_user.is_admin)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_non_admin_phone_never_gets_admin_flags(self):
        normal_user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123",
            first_name="Regular",
            last_name="User",
            telefon="+998901234567",
        )

        self.assertEqual(normalize_phone(normal_user.telefon), "+998901234567")
        self.assertFalse(normal_user.is_admin)
        self.assertFalse(normal_user.is_staff)
        self.assertFalse(normal_user.is_superuser)

    def test_partial_phone_match_does_not_grant_admin_access(self):
        user = User.objects.create_user(
            email="partial@example.com",
            password="StrongPassword123",
            first_name="Partial",
            last_name="Match",
            telefon="+998901649848",
        )

        self.assertEqual(normalize_phone(user.telefon), "+998901649848")
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)


class PendingRegistrationVerificationTests(TestCase):
    def test_pending_registration_generates_secure_verification_token(self):
        pending = PendingRegistration.objects.create(
            first_name="Ali",
            last_name="Valiyev",
            email="ali@example.com",
            telefon="+998991649848",
            password_hash="hashed-password",
            status="pending",
        )

        self.assertTrue(pending.verification_token)
        self.assertTrue(pending.verification_token_hash)
        self.assertIsNotNone(pending.expires_at)
        self.assertEqual(pending.status, "pending")

    def test_verified_pending_registration_can_be_completed_once(self):
        pending = PendingRegistration.objects.create(
            first_name="Laylo",
            last_name="Saidova",
            email="laylo@example.com",
            telefon="+998901234567",
            password_hash="hashed-password",
            status="verified",
            verified_at="2024-01-01T00:00:00Z",
        )

        self.assertTrue(pending.is_verified)
        self.assertFalse(pending.is_used)
        self.assertTrue(pending.can_be_completed)


class DirectRegisterLoginWithoutVerificationTests(TestCase):
    def test_register_creates_user_and_logs_in_without_verification(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "direct-register@example.com",
                "telefon": "+998901234567",
                "password1": "StrongPassword123",
                "password2": "StrongPassword123",
                "agree_terms": "on",
            },
            follow=True,
        )

        self.assertEqual(User.objects.filter(email="direct-register@example.com").count(), 1)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.redirect_chain[-1][0], "/")
        self.assertFalse(PendingRegistration.objects.filter(email="direct-register@example.com").exists())

    def test_login_authenticates_user_without_verification_check(self):
        user = User.objects.create_user(
            email="direct-login@example.com",
            password="StrongPassword123",
            first_name="Direct",
            last_name="Login",
            telefon="+998901234568",
        )

        response = self.client.post(
            reverse("accounts:login"),
            {"email": "direct-login@example.com", "password": "StrongPassword123"},
            follow=True,
        )

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertEqual(response.redirect_chain[-1][0], "/")

    def test_logout_then_login_again_works_without_verification(self):
        user = User.objects.create_user(
            email="logout-login@example.com",
            password="StrongPassword123",
            first_name="Logout",
            last_name="User",
            telefon="+998901234569",
        )

        self.client.login(username=user.email, password="StrongPassword123")
        self.client.logout()

        response = self.client.post(
            reverse("accounts:login"),
            {"email": "logout-login@example.com", "password": "StrongPassword123"},
            follow=True,
        )

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertEqual(response.redirect_chain[-1][0], "/")


class AccountDeletionSecurityTests(TestCase):
    def test_user_can_delete_own_account_with_correct_password(self):
        user = User.objects.create_user(
            email="delete-me@example.com",
            password="StrongPassword123",
            first_name="Delete",
            last_name="Me",
            telefon="+998901234580",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"password": "StrongPassword123"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "Hisobingiz muvaffaqiyatli olib tashlandi.")

    def test_user_cannot_delete_account_with_wrong_password(self):
        user = User.objects.create_user(
            email="wrong-password-delete@example.com",
            password="StrongPassword123",
            first_name="Wrong",
            last_name="Pass",
            telefon="+998901234581",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"password": "WrongPassword"},
            follow=True,
        )

        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertContains(response, "Parol xato kiritildi. Hisob ochirilmadi.")

    def test_get_request_is_rejected_for_account_deletion(self):
        user = User.objects.create_user(
            email="get-delete@example.com",
            password="StrongPassword123",
            first_name="Get",
            last_name="Delete",
            telefon="+998901234582",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:delete_account"), follow=True)

        self.assertEqual(response.status_code, 405)

    def test_user_cannot_delete_another_user_account(self):
        victim = User.objects.create_user(
            email="victim@example.com",
            password="StrongPassword123",
            first_name="Victim",
            last_name="User",
            telefon="+998901234583",
        )
        actor = User.objects.create_user(
            email="actor@example.com",
            password="StrongPassword123",
            first_name="Actor",
            last_name="User",
            telefon="+998901234584",
        )
        self.client.force_login(actor)

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"password": "StrongPassword123", "user_id": victim.pk},
            follow=True,
        )

        self.assertTrue(User.objects.filter(pk=victim.pk).exists())
        self.assertTrue(User.objects.filter(pk=actor.pk).exists())

    def test_admin_account_delete_is_blocked(self):
        admin = User.objects.create_user(
            email="admin-delete@example.com",
            password="StrongPassword123",
            first_name="Admin",
            last_name="Delete",
            telefon="+998991649848",
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"password": "StrongPassword123"},
            follow=True,
        )

        self.assertTrue(User.objects.filter(pk=admin.pk).exists())
        self.assertContains(response, "Administrator hisobini bu yerdan ochirish mumkin emas.")

    def test_delete_invalidates_user_sessions(self):
        user = User.objects.create_user(
            email="session-delete@example.com",
            password="StrongPassword123",
            first_name="Session",
            last_name="Delete",
            telefon="+998901234585",
        )
        self.client.force_login(user)
        session_key = self.client.session.session_key

        response = self.client.post(
            reverse("accounts:delete_account"),
            {"password": "StrongPassword123"},
            follow=True,
        )

        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertContains(response, "Hisobingiz muvaffaqiyatli olib tashlandi.")
        self.assertIsNone(self.client.session.session_key)
