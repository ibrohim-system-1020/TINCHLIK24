from django.urls import path

from . import webhooks

app_name = "bots"

urlpatterns = [
    path("user/webhook/", webhooks.user_telegram_webhook, name="user_telegram_webhook"),
    path("admin/webhook/", webhooks.admin_telegram_webhook, name="admin_telegram_webhook"),
]
