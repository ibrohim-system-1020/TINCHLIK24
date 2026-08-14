import json
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Register Telegram bot webhooks for the configured public domain."

    def add_arguments(self, parser):
        parser.add_argument("--domain", default=getattr(settings, "PUBLIC_BASE_URL", ""), help="Public base URL without trailing slash.")
        parser.add_argument("--user-secret", default=getattr(settings, "USER_BOT_WEBHOOK_SECRET", ""), help="User bot webhook secret.")
        parser.add_argument("--admin-secret", default=getattr(settings, "ADMIN_BOT_WEBHOOK_SECRET", ""), help="Admin bot webhook secret.")

    def handle(self, *args, **options):
        base_url = (options["domain"] or getattr(settings, "PUBLIC_BASE_URL", "") or getattr(settings, "SITE_DOMAIN", "")).rstrip("/")
        if not base_url:
            raise CommandError("PUBLIC_BASE_URL or SITE_DOMAIN must be configured.")

        user_token = getattr(settings, "USER_BOT_TOKEN", "")
        admin_token = getattr(settings, "ADMIN_BOT_TOKEN", "")

        if not user_token:
            raise CommandError("USER_BOT_TOKEN is not configured.")
        if not admin_token:
            raise CommandError("ADMIN_BOT_TOKEN is not configured.")

        user_secret = options["user_secret"] or getattr(settings, "USER_BOT_WEBHOOK_SECRET", "")
        admin_secret = options["admin_secret"] or getattr(settings, "ADMIN_BOT_WEBHOOK_SECRET", "")

        if not user_secret:
            raise CommandError("USER_BOT_WEBHOOK_SECRET is not configured.")
        if not admin_secret:
            raise CommandError("ADMIN_BOT_WEBHOOK_SECRET is not configured.")

        user_url = urljoin(base_url + "/", "telegram/user/webhook/")
        admin_url = urljoin(base_url + "/", "telegram/admin/webhook/")

        self.stdout.write(self.style.WARNING(f"Registering user bot webhook: {user_url}"))
        self.stdout.write(self.style.WARNING(f"Registering admin bot webhook: {admin_url}"))

        user_response = requests.post(
            f"https://api.telegram.org/bot{user_token}/setWebhook",
            data={
                "url": user_url,
                "secret_token": user_secret,
                "drop_pending_updates": True,
            },
            timeout=30,
        )
        user_payload = user_response.json()
        self.stdout.write(json.dumps(user_payload, ensure_ascii=False, indent=2))

        admin_response = requests.post(
            f"https://api.telegram.org/bot{admin_token}/setWebhook",
            data={
                "url": admin_url,
                "secret_token": admin_secret,
                "drop_pending_updates": True,
            },
            timeout=30,
        )
        admin_payload = admin_response.json()
        self.stdout.write(json.dumps(admin_payload, ensure_ascii=False, indent=2))

        if not user_payload.get("ok") or not admin_payload.get("ok"):
            raise CommandError("One or more webhook registrations failed.")

        self.stdout.write(self.style.SUCCESS("Telegram webhooks registered successfully."))
