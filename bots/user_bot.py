import logging
import os
import uuid

try:
    import bots.django_setup as django_setup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import django_setup  # noqa: F401 - Django ORM ni ishga tushiradi

from asgiref.sync import sync_to_async
from django.conf import settings

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from accounts.forms import normalize_phone
from accounts.models import PendingRegistration, User, TelegramOutMessage
from django.utils import timezone


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("user_bot")


# =========================================================
# QUICK REGISTER STATES
# =========================================================

ISM, FAMILIYA, EMAIL, TELEFON, PAROL, PAROL2 = range(6)


# =========================================================
# PENDING REGISTRATION TOPISH
# =========================================================

@sync_to_async
def _find_pending(token: str):
    """
    Saytdan Telegram botga yuborilgan UUID token
    bo'yicha PendingRegistration ni topadi.
    """

    try:
        token_uuid = uuid.UUID(token.strip())

    except (ValueError, TypeError, AttributeError):
        print("❌ NOTO'G'RI TOKEN:", repr(token))
        return None

    pending = PendingRegistration.objects.filter(
        token=token_uuid,
        is_completed=False,
    ).first()

    print("🔎 TOKEN:", token_uuid)
    print("🔎 PENDING:", pending)

    return pending


# =========================================================
# TELEGRAM PROFILE RASMI
# =========================================================

async def _get_profile_photo_url(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
):
    """
    Telegram foydalanuvchisining profil rasmini oladi.
    Profil rasmi bo'lmasa None qaytaradi.
    """

    try:
        photos = await context.bot.get_user_profile_photos(
            telegram_id,
            limit=1,
        )

        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id

            file = await context.bot.get_file(file_id)

            return file.file_path

    except Exception as e:
        logger.warning(
            "Profil rasmini olishda xatolik: %s",
            e,
        )

    return None


def _mask_phone(phone: str) -> str:
    if not phone:
        return phone or ""

    normalized = normalize_phone(phone)
    if not normalized or len(normalized) != 13:
        return phone

    return f"{normalized[:4]} ** *** ** {normalized[-2:]}"


async def contact_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    contact = update.message.contact
    if not contact:
        return

    if contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "❌ Faqat o'zingizning Telegram akkauntingizga tegishli telefon raqamni yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    token = context.user_data.get("registration_token")
    if not token:
        await update.message.reply_text(
            "❌ Registratsiya ma'lumotlari topilmadi. Iltimos saytga qaytib ro'yxatdan o'ting.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    pending = await _find_pending(token)
    if not pending:
        await update.message.reply_text(
            "❌ Registratsiya ma'lumotlari topilmadi yoki vaqtincha eskirgan.\n"
            "Saytga qaytib ro'yxatdan o'ting.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("registration_token", None)
        return

    site_phone = normalize_phone(pending.telefon)
    telegram_phone = normalize_phone(contact.phone_number)

    if not site_phone or not telegram_phone:
        await update.message.reply_text(
            "❌ Telefon raqamni to'g'ri formatda yuboring.\n"
            "Iltimos, Telegram akkauntingizga tegishli kontaktni yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if site_phone != telegram_phone:
        await update.message.reply_text(
            "❌ Telefon raqamlar mos emas.\n\n"
            "Saytda kiritilgan telefon raqam\n"
            "ushbu Telegram akkauntidagi telefon raqam bilan mos kelmadi.\n\n"
            "Saytda ro'yxatdan o'tishda o'zingizning\n"
            "Telegram akkauntingizga tegishli telefon raqamdan foydalaning.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    tg_user = update.effective_user
    photo_url = await _get_profile_photo_url(
        context,
        tg_user.id,
    )

    try:
        code = await _save_pending_telegram(
            pending,
            tg_user.id,
            tg_user.username,
            photo_url,
        )
    except Exception as e:
        logger.exception(
            "PendingRegistrationni saqlashda xato: %s",
            e,
        )
        await update.message.reply_text(
            "❌ Ichki xatolik yuz berdi. Iltimos, birozdan keyin qayta urinib ko'ring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    context.user_data.pop("registration_token", None)

    await update.message.reply_text(
        "✅ Telefon raqamingiz tasdiqlandi.\n\n"
        "🔐 TINCHLIK tasdiqlash kodi:\n\n"
        f"{code}\n\n"
        "Kod cheklangan vaqt davomida amal qiladi.\n"
        "Saytdagi tasdiqlash oynasiga ushbu kodni kiriting.",
        reply_markup=ReplyKeyboardRemove(),
    )

    logger.info(
        "Verification code Telegram ID %s uchun yuborildi.",
        tg_user.id,
    )


# =========================================================
# PENDING REGISTRATIONGA TELEGRAMNI BOG'LASH
# =========================================================

@sync_to_async
def _save_pending_telegram(
    pending,
    telegram_id,
    username,
    photo_url,
):
    """
    Telegram akkauntini pending registration bilan bog'laydi
    va verification code yaratadi.
    """

    pending.telegram_id = telegram_id
    pending.telegram_username = username
    pending.telegram_photo_url = photo_url

    # Model ichidagi verification code generator
    pending.generate_code()

    # Barcha o'zgarishlar DB ga yozilishi kafolatlanadi
    pending.save()

    return pending.code


# =========================================================
# EMAIL / TELEFON TEKSHIRISH
# =========================================================

@sync_to_async
def _email_or_phone_taken(email, telefon):
    email = str(email).strip().lower()
    telefon = normalize_phone(telefon) or str(telefon).strip()

    email_exists = User.objects.filter(
        email__iexact=email
    ).exists()

    phone_exists = User.objects.filter(
        telefon=telefon
    ).exists()

    return email_exists or phone_exists


# =========================================================
# TELEGRAM ORQALI DIRECT USER YARATISH
# =========================================================

@sync_to_async
def _create_user_via_telegram(
    data,
    telegram_id,
    username,
    photo_url,
):
    """
    Telegram orqali to'g'ridan-to'g'ri ro'yxatdan o'tgan
    foydalanuvchini Django User jadvaliga yaratadi.
    """

    email = data["email"].strip().lower()

    user = User.objects.create_user(
        username=email,
        email=email,
        password=data["parol"],
        first_name=data["ism"],
        last_name=data["familiya"],
        telefon=data["telefon"],
        is_phone_verified=True,
        registered_via=User.RegisteredVia.TELEGRAM,
        telegram_id=telegram_id,
        telegram_username=username,
        telegram_photo_url=photo_url,
    )

    return user


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    args = context.args

    payload = args[0] if args else ""

    print("📩 TELEGRAM PAYLOAD:", repr(payload))


    # -----------------------------------------------------
    # SAYTDAN REGISTRATION
    # /start reg_UUID
    # -----------------------------------------------------

    if payload.startswith("reg_"):

        token = payload.removeprefix("reg_").strip()

        print("🔑 TOKEN STRING:", repr(token))

        pending = await _find_pending(token)

        if not pending:
            await update.message.reply_text(
                "❌ Havola eskirgan yoki noto'g'ri.\n\n"
                "Saytga qaytib ro'yxatdan o'tishni "
                "qaytadan boshlang."
            )

            return ConversationHandler.END

        context.user_data["registration_token"] = str(pending.token)

        await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━\n"
            "📱 Telefon raqamni tasdiqlash\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Saytda kiritgan telefon raqamingiz\n"
            "Telegram akkauntingizdagi raqam bilan mos bo'lishi kerak.\n\n"
            "Quyidagi tugma orqali o'z telefon raqamingizni tasdiqlang.\n",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton(
                            "📱 Telefon raqamni tasdiqlash",
                            request_contact=True,
                        )
                    ]
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )

        return ConversationHandler.END


    # -----------------------------------------------------
    # TELEGRAM ORQALI TO'G'RIDAN-TO'G'RI REGISTER
    # /start quickreg
    # -----------------------------------------------------

    if payload == "quickreg":

        context.user_data.clear()

        await update.message.reply_text(
            "👤 Telegram orqali ro'yxatdan o'tish\n\n"
            "Ismingizni kiriting:"
        )

        return ISM


    # -----------------------------------------------------
    # ODDIY /START
    # -----------------------------------------------------

    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Bu TINCHLIK | MFY verification boti.\n\n"
        "Saytda ro'yxatdan o'tishni boshlab, "
        "Telegram tasdiqlash tugmasini bosing."
    )

    return ConversationHandler.END


# =========================================================
# QUICK REGISTER - ISM
# =========================================================

async def quickreg_ism(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    ism = update.message.text.strip()

    if len(ism) < 2:
        await update.message.reply_text(
            "❌ Ism juda qisqa.\n"
            "Ismingizni qaytadan kiriting:"
        )

        return ISM

    context.user_data["ism"] = ism

    await update.message.reply_text(
        "Familiyangizni kiriting:"
    )

    return FAMILIYA


# =========================================================
# QUICK REGISTER - FAMILIYA
# =========================================================

async def quickreg_familiya(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    familiya = update.message.text.strip()

    if len(familiya) < 2:
        await update.message.reply_text(
            "❌ Familiya juda qisqa.\n"
            "Qaytadan kiriting:"
        )

        return FAMILIYA

    context.user_data["familiya"] = familiya

    await update.message.reply_text(
        "📧 Email manzilingizni kiriting:"
    )

    return EMAIL


# =========================================================
# QUICK REGISTER - EMAIL
# =========================================================

async def quickreg_email(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    email = update.message.text.strip().lower()

    if (
        "@" not in email
        or "." not in email.split("@")[-1]
    ):
        await update.message.reply_text(
            "❌ Email noto'g'ri.\n\n"
            "Masalan:\n"
            "example@gmail.com\n\n"
            "Emailni qaytadan kiriting:"
        )

        return EMAIL

    context.user_data["email"] = email


    keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(
                    "📱 Raqamni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


    await update.message.reply_text(
        "📱 Telefon raqamingizni yuboring.\n\n"
        "Pastdagi tugmani bosing yoki qo'lda yozing.\n\n"
        "Masalan:\n"
        "+998901234567",
        reply_markup=keyboard,
    )

    return TELEFON


# =========================================================
# QUICK REGISTER - TELEFON
# =========================================================

async def quickreg_telefon(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.message.contact:
        telefon = normalize_phone(update.message.contact.phone_number)
    else:
        telefon = normalize_phone(update.message.text.strip())

    if not telefon:
        await update.message.reply_text(
            "❌ Telefon raqam noto'g'ri.\n"
            "Iltimos, +998901234567 shaklida yuboring.",
        )
        return TELEFON

    context.user_data["telefon"] = telefon

    taken = await _email_or_phone_taken(
        context.user_data["email"],
        telefon,
    )


    if taken:

        await update.message.reply_text(
            "❌ Bu email yoki telefon raqam "
            "allaqachon ro'yxatdan o'tgan.\n\n"
            "/start bosib qaytadan urinib ko'ring.",
            reply_markup=ReplyKeyboardRemove(),
        )

        context.user_data.clear()

        return ConversationHandler.END


    await update.message.reply_text(
        "🔑 Parol o'ylab toping.\n\n"
        "Parol kamida 8 ta belgidan iborat bo'lsin:",
        reply_markup=ReplyKeyboardRemove(),
    )

    return PAROL


# =========================================================
# QUICK REGISTER - PAROL
# =========================================================

async def quickreg_parol(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    parol = update.message.text.strip()

    if len(parol) < 8:

        await update.message.reply_text(
            "❌ Parol juda qisqa.\n\n"
            "Kamida 8 ta belgi kiriting:"
        )

        return PAROL


    context.user_data["parol"] = parol


    # Telegram chatda parol qolib ketmasligi uchun
    # foydalanuvchi yuborgan xabarni o'chirishga harakat qilamiz.
    try:
        await update.message.delete()
    except Exception:
        pass


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔐 Parolni yana bir marta kiriting:",
    )

    return PAROL2


# =========================================================
# QUICK REGISTER - PAROLNI TASDIQLASH
# =========================================================

async def quickreg_parol2(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    parol2 = update.message.text.strip()


    try:
        await update.message.delete()
    except Exception:
        pass


    if parol2 != context.user_data.get("parol"):

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "❌ Parollar mos emas.\n\n"
                "Yangi parolni qaytadan kiriting:"
            ),
        )

        return PAROL


    tg_user = update.effective_user


    photo_url = await _get_profile_photo_url(
        context,
        tg_user.id,
    )


    try:

        await _create_user_via_telegram(
            context.user_data,
            tg_user.id,
            tg_user.username,
            photo_url,
        )

    except Exception as e:

        logger.exception(
            "Telegram orqali user yaratishda xato: %s",
            e,
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "❌ Ro'yxatdan o'tishda xatolik yuz berdi.\n\n"
                "Saytda qaytadan urinib ko'ring."
            ),
        )

        return ConversationHandler.END


    context.user_data.clear()


    site_domain = getattr(
        settings,
        "SITE_DOMAIN",
        "http://127.0.0.1:8007",
    )


    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
            "Endi saytda email va parolingiz "
            "orqali kirishingiz mumkin.\n\n"
            f"🌐 {site_domain}/login/"
        ),
    )


    return ConversationHandler.END


# =========================================================
# CANCEL
# =========================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Ro'yxatdan o'tish bekor qilindi.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.exception(
        "Botda xatolik yuz berdi:",
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not settings.USER_BOT_TOKEN:

        raise RuntimeError(
            "USER_BOT_TOKEN .env faylida ko'rsatilmagan"
        )


    app = (
        Application
        .builder()
        .token(settings.USER_BOT_TOKEN)
        .build()
    )


    conversation = ConversationHandler(

        entry_points=[
            CommandHandler(
                "start",
                start,
            )
        ],

        states={

            ISM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    quickreg_ism,
                )
            ],

            FAMILIYA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    quickreg_familiya,
                )
            ],

            EMAIL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    quickreg_email,
                )
            ],

            TELEFON: [
                MessageHandler(
                    (
                        filters.TEXT
                        | filters.CONTACT
                    )
                    & ~filters.COMMAND,
                    quickreg_telefon,
                )
            ],

            PAROL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    quickreg_parol,
                )
            ],

            PAROL2: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    quickreg_parol2,
                )
            ],

        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            )
        ],

        allow_reentry=True,
    )


    app.add_handler(conversation)

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            contact_handler,
        )
    )

    app.add_error_handler(
        error_handler
    )


    logger.info(
        "✅ User bot ishga tushdi..."
    )

    if os.getenv("USE_LOCAL_BOT_POLLING", "").lower() not in {"1", "true", "yes", "on"}:
        logger.info("Webhook mode enabled for user bot; polling is disabled for deployment.")
        return

    app.run_polling(
        drop_pending_updates=False,
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()