import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import Update

from bots.admin.handlers import (
    SEARCH_TERM,
    handle_callback,
    search_cancel,
    search_term,
    start,
)
from bots.user_bot import (
    ISM,
    FAMILIYA,
    EMAIL,
    TELEFON,
    PAROL,
    PAROL2,
    cancel,
    contact_handler,
    quickreg_email,
    quickreg_familiya,
    quickreg_ism,
    quickreg_parol,
    quickreg_parol2,
    quickreg_telefon,
    start as user_start,
)
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

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
def user_telegram_webhook(request: HttpRequest):
    if request.method != "POST":
        return HttpResponse(status=405)

    if not _validate_webhook_request(request, "user"):
        return HttpResponse(status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False}, status=400)

    app = _get_user_application()
    update = Update.de_json(payload, app.bot)
    if update is None:
        return JsonResponse({"ok": False}, status=400)

    try:
        app.process_update(update)
    except Exception:
        logger.exception("User webhook update processing failed.")
        return JsonResponse({"ok": False}, status=500)

    return JsonResponse({"ok": True})


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


def _get_user_application() -> Application:
    app = Application.builder().token(settings.USER_BOT_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", user_start)],
        states={
            ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, quickreg_ism)],
            FAMILIYA: [MessageHandler(filters.TEXT & ~filters.COMMAND, quickreg_familiya)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, quickreg_email)],
            TELEFON: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, quickreg_telefon)],
            PAROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, quickreg_parol)],
            PAROL2: [MessageHandler(filters.TEXT & ~filters.COMMAND, quickreg_parol2)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conversation)
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_error_handler(lambda update, context: logger.exception("User bot xatolik: %s", context.error))
    return app


def _get_admin_application() -> Application:
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
