import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

try:
    from telegram import Update
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
    TELEGRAM_AVAILABLE = True
except Exception:
    Update = None
    Application = None
    CallbackQueryHandler = None
    CommandHandler = None
    ConversationHandler = None
    MessageHandler = None
    filters = None
    TELEGRAM_AVAILABLE = False

from bots.admin.handlers import (
    SEARCH_TERM,
    handle_callback,
    search_cancel,
    search_term,
    start,
)

logger = logging.getLogger("telegram_webhooks")


def _get_secret(bot_type: str) -> str:
    return getattr(settings, f"{bot_type.upper()}_BOT_WEBHOOK_SECRET", "")


def _validate_webhook_request(request: HttpRequest, bot_type: str) -> bool:
    expected = _get_secret(bot_type)
    if not expected:
        logger.warning("No webhook secret configured for %s bot.", bot_type)
        return False

    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or request.POST.get("secret")
    return provided == expected


@csrf_exempt
def admin_telegram_webhook(request: HttpRequest):
    if request.method != "POST":
        return HttpResponse(status=405)

    if not _validate_webhook_request(request, "admin"):
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False}, status=400)

    if not TELEGRAM_AVAILABLE:
        logger.warning("Telegram package not installed; webhook disabled.")
        return JsonResponse({"ok": False}, status=503)

    app = _get_admin_application()
    update = Update.de_json(payload, app.bot)
    if update is None:
        return JsonResponse({"ok": False}, status=400)

    try:
        app.process_update(update)
    except Exception:
        logger.exception("Admin webhook update processing failed.")
        return JsonResponse({"ok": False}, status=500)

    return JsonResponse({"ok": True})


def _get_admin_application() -> Application:
    if not TELEGRAM_AVAILABLE:
        raise RuntimeError("telegram package is not available")

    app = Application.builder().token(settings.ADMIN_BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SEARCH_TERM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_term),
            ],
        },
        fallbacks=[CommandHandler("cancel", search_cancel)],
        allow_reentry=True,
    )

    app.add_handler(conversation)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(lambda update, context: logger.exception("Admin bot xatolik: %s", context.error))
    return app
