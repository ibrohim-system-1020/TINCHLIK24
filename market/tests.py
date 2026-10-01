from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Listing


User = get_user_model()


class ListingContactPrivacyTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email="market-seller@example.test",
            password="StrongPassword123",
            first_name="Market",
            last_name="Seller",
            telefon="+998901234587",
        )
        self.listing = Listing.objects.create(
            seller=self.seller,
            title="Private contact listing",
            description="A listing used to test seller contact privacy.",
            price=250000,
            category="phone",
            status=Listing.STATUS_APPROVED,
        )
        self.detail_url = reverse("market:listing_detail", args=[self.listing.pk])

    def test_contact_values_stay_private_until_owner_opts_in(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.seller.email)
        self.assertNotContains(response, self.seller.telefon)
        self.assertContains(response, "Ko‘rsatilmagan")

        self.seller.market_phone_visible = True
        self.seller.market_email_visible = True
        self.seller.save(update_fields=["market_phone_visible", "market_email_visible"])

        response = self.client.get(self.detail_url)
        self.assertContains(response, f"tel:{self.seller.telefon}")
        self.assertContains(response, f"mailto:{self.seller.email}")

    def test_owner_can_update_contact_visibility_from_profile(self):
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse("accounts:profile"),
            {"market_phone_visible": "on", "market_email_visible": "on"},
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.market_phone_visible)
        self.assertTrue(self.seller.market_email_visible)

        self.client.post(reverse("accounts:profile"), {})
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.market_phone_visible)
        self.assertFalse(self.seller.market_email_visible)

    def test_phone_visibility_cannot_be_enabled_without_a_phone(self):
        seller_without_phone = User.objects.create_user(
            email="no-phone@example.test",
            password="StrongPassword123",
            first_name="No",
            last_name="Phone",
        )
        self.client.force_login(seller_without_phone)

        response = self.client.post(
            reverse("accounts:profile"),
            {"market_phone_visible": "on"},
        )

        self.assertEqual(response.status_code, 200)
        seller_without_phone.refresh_from_db()
        self.assertFalse(seller_without_phone.market_phone_visible)
        self.assertContains(response, "Telefon raqami profilingizda mavjud emas.")

    def test_all_listings_shows_every_approved_listing_and_keeps_moderation(self):
        another_seller = User.objects.create_user(
            email="another-market-seller@example.test",
            password="StrongPassword123",
            first_name="Another",
            last_name="Seller",
            telefon="+998901234589",
        )
        another_approved = Listing.objects.create(
            seller=another_seller,
            title="Approved computer listing",
            description="Another public listing.",
            price=500000,
            category="computer",
            status=Listing.STATUS_APPROVED,
        )
        pending = Listing.objects.create(
            seller=self.seller,
            title="Pending listing stays private",
            description="This listing has not passed moderation.",
            price=350000,
            status=Listing.STATUS_PENDING,
        )

        response = self.client.get(reverse("market:listings"))
        self.assertContains(response, self.listing.title)
        self.assertContains(response, another_approved.title)
        self.assertContains(response, pending.title)
        self.assertContains(response, "Yangi e'lonlar")
        self.assertContains(response, "Moderatsiya kutilmoqda")
        self.assertNotIn(pending.pk, [item.pk for item in response.context["listings"].object_list])
        self.assertContains(response, 'href="/market/"')
        self.assertContains(response, "Hamma e'lonlar")
        self.assertContains(response, f'href="{reverse("market:listing_detail", args=[self.listing.pk])}"')
        self.assertContains(response, "Hudud ko‘rsatilmagan")

        filtered_response = self.client.get(reverse("market:listings"), {"category": "phone"})
        self.assertContains(filtered_response, self.listing.title)
        self.assertNotContains(filtered_response, another_approved.title)

    def test_admin_can_approve_pending_listing_for_public_market(self):
        moderator = User.objects.create_user(
            email="market-moderator@example.test",
            password="StrongPassword123",
            first_name="Market",
            last_name="Moderator",
            telefon="+998901234588",
        )
        moderator.is_staff = True
        moderator.is_superuser = True
        moderator.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(moderator)
        self.listing.status = Listing.STATUS_PENDING
        self.listing.save(update_fields=["status"])

        response = self.client.post(
            reverse("admin:market_listing_changelist"),
            {
                "action": "approve_listings",
                "_selected_action": [str(self.listing.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.STATUS_APPROVED)
        public_response = self.client.get(reverse("market:listings"))
        self.assertContains(public_response, self.listing.title)
        self.assertContains(public_response, "Tasdiqlangan")

    def test_admin_can_reject_pending_listing_and_keep_it_out_of_public_market(self):
        moderator = User.objects.create_user(
            email="market-reject-moderator@example.test",
            password="StrongPassword123",
            first_name="Market",
            last_name="Moderator",
            telefon="+998901234591",
        )
        moderator.is_staff = True
        moderator.is_superuser = True
        moderator.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(moderator)
        self.listing.status = Listing.STATUS_PENDING
        self.listing.save(update_fields=["status"])

        response = self.client.post(
            reverse("admin:market_listing_changelist"),
            {
                "action": "reject_listings",
                "_selected_action": [str(self.listing.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.STATUS_REJECTED)
        public_response = Client().get(reverse("market:listings"))
        self.assertNotContains(public_response, self.listing.title)
        self.assertNotContains(public_response, "Yangi e'lonlar")
        self.assertEqual(Client().get(self.detail_url).status_code, 404)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.detail_url).status_code, 200)

    def test_new_listing_is_public_to_other_users_after_creation(self):
        self.client.force_login(self.seller)
        uploads = []
        for index in range(3):
            content = BytesIO()
            Image.new("RGB", (8, 8), color=(30 * index, 100, 180)).save(content, format="PNG")
            uploads.append(SimpleUploadedFile(
                f"market-upload-{index}.png",
                content.getvalue(),
                content_type="image/png",
            ))

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse("market:create_listing"), {
                "title": "Visible to all users",
                "description": "Approved on listing creation.",
                "price": "420000",
                "condition": Listing.CONDITION_NEW,
                "category": "phone",
                "neighborhood": "Tinchlik",
                "images": uploads,
            })

            listing = Listing.objects.get(title="Visible to all users")
            self.assertEqual(listing.status, Listing.STATUS_PENDING)
            self.assertRedirects(
                response,
                reverse("market:listing_detail", args=[listing.pk]),
                fetch_redirect_response=False,
            )
            self.assertEqual(listing.images.count(), 3)
            self.assertTrue(all(image.image.storage.exists(image.image.name) for image in listing.images.all()))
            my_listings_response = self.client.get(reverse("market:my_listings"))
            self.assertContains(my_listings_response, listing.title)
            self.assertContains(my_listings_response, "Moderatsiya kutilmoqda")

            other_user = User.objects.create_user(
                email="other-market-user@example.test",
                password="StrongPassword123",
                first_name="Other",
                last_name="User",
                telefon="+998901234590",
            )
            other_client = Client()
            other_client.force_login(other_user)
            response = other_client.get(reverse("market:listings"))

        self.assertContains(response, listing.title)
        self.assertContains(response, listing.seller.get_full_name())
        self.assertContains(response, "Moderatsiya kutilmoqda")
        self.assertNotIn(listing.pk, [item.pk for item in response.context["listings"].object_list])
        self.assertEqual(response.context["new_listings"][0].pk, listing.pk)
        self.assertContains(response, reverse("market:listing_detail", args=[listing.pk]))

    def test_home_shows_recent_approved_listings_in_both_preview_sections(self):
        recent_seller = User.objects.create_user(
            email="recent-home-seller@example.test",
            password="StrongPassword123",
            first_name="Recent",
            last_name="Seller",
            telefon="+998901234592",
        )
        recent_listing = Listing.objects.create(
            seller=recent_seller,
            title="Recent approved homepage listing",
            description="This approved listing should preview on the homepage.",
            price=750000,
            category="home",
            neighborhood="Navoiy",
            status=Listing.STATUS_APPROVED,
        )
        pending_listing = Listing.objects.create(
            seller=self.seller,
            title="Pending homepage listing stays private",
            description="This listing must wait for moderation.",
            price=640000,
            status=Listing.STATUS_PENDING,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["latest_listings"][0].pk, recent_listing.pk)
        self.assertContains(response, 'class="home-market-preview-card"', count=4)
        self.assertContains(response, recent_listing.title)
        self.assertNotContains(response, pending_listing.title)
        self.assertContains(response, reverse("market:listing_detail", args=[recent_listing.pk]))
        self.assertContains(response, "Navoiy")