import logging
import os

try:
    import bots.django_setup as django_setup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import django_setup  # noqa: F401  # noqa: F401 - Django ORM ni ishga tushiradi
from django.conf import settings
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bots.admin.handlers import (
    SEARCH_TERM,
    handle_callback,
    search_cancel,
    search_term,
    start,
)

logger = logging.getLogger("admin_bot")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Admin bot xatolik: %s", context.error)


def main():
    if not settings.ADMIN_BOT_TOKEN:
        raise RuntimeError("ADMIN_BOT_TOKEN .env faylida ko'rsatilmagan")

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
    app.add_error_handler(error_handler)

    logger.info("✅ Admin bot ishga tushdi...")
    if os.getenv("USE_LOCAL_BOT_POLLING", "").lower() not in {"1", "true", "yes", "on"}:
        logger.info("Webhook mode enabled for admin bot; polling is disabled for deployment.")
        return
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
