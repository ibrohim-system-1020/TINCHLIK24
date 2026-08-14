import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check the active Telegram webhook configuration for both bots."

    def handle(self, *args, **options):
        user_token = getattr(settings, "USER_BOT_TOKEN", "")
        admin_token = getattr(settings, "ADMIN_BOT_TOKEN", "")

        if not user_token:
            raise CommandError("USER_BOT_TOKEN is not configured.")
        if not admin_token:
            raise CommandError("ADMIN_BOT_TOKEN is not configured.")

        for label, token in [("user", user_token), ("admin", admin_token)]:
            response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=30)
            payload = response.json()
            self.stdout.write(f"--- {label} bot ---")
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))

            if not payload.get("ok"):
                raise CommandError(f"Failed to fetch webhook info for {label} bot.")
