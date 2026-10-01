from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from adminpanel.models import Announcement
from market.models import Listing


class HomePageRenderingTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			email="resident@example.com",
			password="StrongPassword123",
			first_name="Dilshod",
			last_name="Karimov",
			telefon="+998901234561",
		)

	def test_homepage_uses_public_announcements_and_approved_listings(self):
		Announcement.objects.create(
			title="Mahalla xabari",
			text="Jamoa uchun tasdiqlangan ma'lumot.",
			target_all=True,
			target_online_only=False,
		)
		Listing.objects.create(
			seller=self.user,
			title="Sotuvdagi velosiped",
			description="Yaxshi holatdagi velosiped.",
			price=1200000,
			status=Listing.STATUS_APPROVED,
		)

		response = self.client.get(reverse("home"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Mahalla xabari")
		self.assertContains(response, "Sotuvdagi velosiped")
		self.assertNotContains(response, "Alisher Qodirov")

	def test_profile_displays_real_account_data_and_available_tabs(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse("accounts:profile"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Dilshod Karimov")
		self.assertContains(response, self.user.telefon)
		self.assertContains(response, 'id="history-panel"')
		self.assertContains(response, 'id="listings-panel"')
