import json
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Register the admin Telegram webhook for the configured public domain."

    def add_arguments(self, parser):
        parser.add_argument("--domain", default=getattr(settings, "PUBLIC_BASE_URL", ""), help="Public base URL without trailing slash.")
        parser.add_argument("--admin-secret", default=getattr(settings, "ADMIN_BOT_WEBHOOK_SECRET", ""), help="Admin bot webhook secret.")

    def handle(self, *args, **options):
        base_url = (options["domain"] or getattr(settings, "PUBLIC_BASE_URL", "") or getattr(settings, "SITE_DOMAIN", "")).rstrip("/")
        if not base_url:
            raise CommandError("PUBLIC_BASE_URL or SITE_DOMAIN must be configured.")

        admin_token = getattr(settings, "ADMIN_BOT_TOKEN", "")
        if not admin_token:
            raise CommandError("ADMIN_BOT_TOKEN is not configured.")

        admin_secret = options["admin_secret"] or getattr(settings, "ADMIN_BOT_WEBHOOK_SECRET", "")
        if not admin_secret:
            raise CommandError("ADMIN_BOT_WEBHOOK_SECRET is not configured.")

        admin_url = urljoin(base_url + "/", "telegram/admin/webhook/")
        self.stdout.write(self.style.WARNING(f"Registering admin bot webhook: {admin_url}"))

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

        if not admin_payload.get("ok"):
            raise CommandError("Admin webhook registration failed.")

        self.stdout.write(self.style.SUCCESS("Admin Telegram webhook registered successfully."))
