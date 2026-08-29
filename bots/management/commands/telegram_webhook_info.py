import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check the active Telegram admin webhook configuration."

    def handle(self, *args, **options):
        admin_token = getattr(settings, "ADMIN_BOT_TOKEN", "")
        if not admin_token:
            raise CommandError("ADMIN_BOT_TOKEN is not configured.")

        response = requests.get(f"https://api.telegram.org/bot{admin_token}/getWebhookInfo", timeout=30)
        payload = response.json()
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))

        if not payload.get("ok"):
            raise CommandError("Failed to fetch webhook info for the admin bot.")
