import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.conf import settings
from typing import Any

try:
    from telegram import Update
    from telegram.ext import CallbackContext, ConversationHandler, filters
    TELEGRAM_AVAILABLE = True
except Exception:
    Update = Any
    CallbackContext = Any
    ConversationHandler = None
    filters = None
    TELEGRAM_AVAILABLE = False

from .keyboards import (
    back_to_main_keyboard,
    confirm_message_keyboard,
    main_menu_keyboard,
    user_action_keyboard,
    users_list_keyboard,
    users_pagination_keyboard,
)
from .services import (
    create_audit_log,
    get_dashboard_stats,
    get_all_time_top_users,
    get_recent_audit_logs,
    get_user_by_id,
    get_user_by_search,
    get_user_list,
    get_user_login_count,
    get_user_login_history,
    get_weekly_top_users,
)
from .utils import format_user_card, is_admin_telegram_id


SEARCH_TERM = 1


async def start(update: Update, context: CallbackContext):
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ Siz admin emassiz yoki sizga ruxsat berilmagan."
        )
        return

    await update.message.reply_text(
        "📊 TINCHLIK | MFY Admin Panel\n\n" "Quyidagi menyudan tanlang:",
        reply_markup=main_menu_keyboard(),
    )


async def is_admin(update: Update) -> bool:
    admin_id = update.effective_user.id
    return is_admin_telegram_id(admin_id)


async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not await is_admin(update):
        await query.answer()
        await query.edit_message_text(
            "❌ Siz admin emassiz yoki sizga ruxsat berilmagan.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "admin:main":
        await query.edit_message_text(
            "📊 TINCHLIK | MFY Admin Panel\n\n" "Quyidagi menyudan tanlang:",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "admin:dashboard":
        stats = await get_dashboard_stats()
        text = (
            "📊 TINCHLIK | MFY ADMIN\n\n"
            f"👥 Umumiy foydalanuvchilar: {stats['total_users']}\n"
            f"🟢 Online: {stats['online_users']}\n"
            f"🆕 Bugun qo'shilgan: {stats['today_users']}\n"
            f"📅 Oxirgi 7 kun: {stats['week_users']}\n"
            f"📆 Oxirgi 30 kun: {stats['month_users']}\n\n"
            f"✅ Tasdiqlangan: {stats['verified_users']}\n"
            f"📱 Telegram ulangan: {stats['telegram_users']}\n"
            f"🔐 Umumiy loginlar: {stats['total_logins']}\n"
        )
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())
        return

    if data == "admin:users":
        await show_users_page(query, 1)
        return

    if data and data.startswith("admin:users:page:"):
        page = int(data.rsplit(":", 1)[-1])
        await show_users_page(query, page)
        return

    if data == "admin:search":
        await query.edit_message_text(
            "🔎 Foydalanuvchini izlang. Iltimos, qidiruv so‘zini yuboring.",
            reply_markup=back_to_main_keyboard(),
        )
        context.user_data["admin_state"] = "search"
        return

    if data == "admin:online":
        await show_online_users(query)
        return

    if data == "admin:ranking":
        await show_ranking(query)
        return

    if data == "admin:stats":
        await show_stats(query)
        return

    if data == "admin:security":
        await query.edit_message_text(
            "🔐 Xavfsizlik bo‘limi hozircha ishlab chiqilmoqda."
            "\n\nAdmin bot MVP uchun boshqa bo‘limlarni tanlang.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "admin:audit":
        await show_audit_log(query)
        return

    if data == "admin:logout":
        await query.edit_message_text(
            "✅ Siz admin menyusidan chiqdingiz.",
        )
        return

    if data and data.startswith("admin:user:view:"):
        user_id = int(data.split(":")[-1])
        await show_user_profile(query, user_id)
        return

    if data and data.startswith("admin:user:history:"):
        user_id = int(data.split(":")[-1])
        await show_user_history(query, user_id)
        return

    if data and data.startswith("admin:user:message:"):
        user_id = int(data.split(":")[-1])
        await query.edit_message_text(
            "📨 Admin xabarini yozing. Keyin tasdiqlash uchun yuboring:",
            reply_markup=back_to_main_keyboard(),
        )
        context.user_data["admin_state"] = "message"
        context.user_data["pending_message_user"] = user_id
        context.user_data.pop("pending_message_text", None)
        return

    if data and data.startswith("admin:user:verify:"):
        user_id = int(data.split(":")[-1])
        await verify_user(query, context, user_id)
        return

    if data == "admin:message:confirm":
        await confirm_send_message(query, context)
        return

    if data == "admin:message:cancel":
        await cancel_send_message(query, context)
        return

    if data == "admin:noop":
        return

    await query.edit_message_text(
        "❌ Noto‘g‘ri buyruq. Iltimos bosh menyuga qayting.",
        reply_markup=main_menu_keyboard(),
    )


async def show_users_page(query, page: int = 1):
    page_size = 8
    users, total = await get_user_list(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    if not users:
        await query.edit_message_text(
            "👥 Foydalanuvchilar topilmadi.",
            reply_markup=back_to_main_keyboard(),
        )
        return

    text = "👥 Foydalanuvchilar ro‘yxati\n\n"
    for user in users:
        text += f"{user.id}. {user.first_name or '-'} {user.last_name or '-'} | {user.email} | @{user.telegram_username or '-'}\n"
    text += f"\nSahifa {page} / {total_pages}"

    await query.edit_message_text(
        text,
        reply_markup=users_list_keyboard(users),
    )


async def show_user_profile(query, user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Foydalanuvchi topilmadi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    login_count = await get_user_login_count(user)
    text = format_user_card(user, login_count, settings.ONLINE_THRESHOLD_MINUTES)
    await query.edit_message_text(
        text,
        reply_markup=user_action_keyboard(user.id, user.is_online, user.is_phone_verified),
    )


async def show_user_history(query, user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Foydalanuvchi topilmadi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    history = await get_user_login_history(user)
    lines = ["🕘 Login tarixi\n"]
    if not history:
        lines.append("Hozircha kirishlar mavjud emas.")
    else:
        for item in history:
            timestamp = item.logged_in_at.strftime("%d.%m.%Y %H:%M")
            ip = item.ip_address or "–"
            lines.append(f"• {timestamp} | IP: {ip}")
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=back_to_main_keyboard(),
    )


async def show_online_users(query):
    stats = await get_dashboard_stats()
    await query.edit_message_text(
        f"🟢 Hozir online: {stats['online_users']}\n\n"
        "Bu bo‘lim keyinchalik to‘liq foydalanuvchi ro‘yxati bilan kengaytiriladi.",
        reply_markup=main_menu_keyboard(),
    )


async def show_ranking(query):
    weekly = await get_weekly_top_users()
    all_time = await get_all_time_top_users()
    lines = ["🏆 REYTINGLAR\n"]
    lines.append("🥇 HAFTALIK TOP (7 kunlik loginlar bo‘yicha):")
    for idx, user in enumerate(weekly, start=1):
        lines.append(f"{idx}. {user.first_name or '-'} {user.last_name or '-'} — {user.week_logins} login")
    lines.append("\n🥇 UMUMIY TOP (barcha loginlar bo‘yicha):")
    for idx, user in enumerate(all_time, start=1):
        lines.append(f"{idx}. {user.first_name or '-'} {user.last_name or '-'} — {user.total_logins} login")
    await query.edit_message_text("\n".join(lines), reply_markup=main_menu_keyboard())


async def show_stats(query):
    stats = await get_dashboard_stats()
    await query.edit_message_text(
        "📈 STATISTIKA\n\n"
        f"Bugun: {stats['today_users']} yangi user\n"
        f"7 kun: {stats['week_users']} yangi user\n"
        f"30 kun: {stats['month_users']} yangi user\n"
        f"Umumiy: {stats['total_users']} user\n\n"
        f"✅ Verifikatsiya qilingan: {stats['verified_users']}\n"
        f"📱 Telegram ulangan: {stats['telegram_users']}\n"
        f"🔐 Umumiy loginlar: {stats['total_logins']}\n",
        reply_markup=main_menu_keyboard(),
    )


async def show_audit_log(query):
    logs = await get_recent_audit_logs()
    if not logs:
        await query.edit_message_text(
            "🧾 Audit log bo‘sh.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["🧾 AUDIT LOG\n"]
    for item in logs[:10]:
        target = item.target_user.email if item.target_user else "—"
        lines.append(
            f"• {item.created_at.strftime('%d.%m.%Y %H:%M')} | {item.action} | admin: {item.admin_username or item.admin_telegram_id} | target: {target}"
        )
    await query.edit_message_text("\n".join(lines), reply_markup=main_menu_keyboard())


async def verify_user(query, context: CallbackContext, user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Foydalanuvchi topilmadi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    if user.is_phone_verified:
        await query.edit_message_text(
            "✅ Bu foydalanuvchi allaqachon tasdiqlangan.",
            reply_markup=user_action_keyboard(user.id, user.is_online, user.is_phone_verified),
        )
        return

    user.is_phone_verified = True
    await sync_to_async(user.save)()
    admin_user = query.from_user
    await create_audit_log(
        admin_telegram_id=admin_user.id,
        admin_username=admin_user.username,
        action=f"User tasdiqlandi: {user.email}",
        target_user=user,
    )
    await query.edit_message_text(
        "✅ Foydalanuvchi tasdiqlandi.",
        reply_markup=user_action_keyboard(user.id, user.is_online, user.is_phone_verified),
    )


async def confirm_send_message(query, context: CallbackContext):
    user_id = context.user_data.get("pending_message_user")
    message_text = context.user_data.get("pending_message_text")

    if not user_id or not message_text:
        await query.edit_message_text(
            "❌ Xabar yuborish uchun foydalanuvchi yoki matn topilmadi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    user = await get_user_by_id(user_id)
    if not user or not user.telegram_id:
        await query.edit_message_text(
            "❌ Bu foydalanuvchi Telegram bilan bog‘lanmagan yoki topilmadi.",
            reply_markup=main_menu_keyboard(),
        )
        context.user_data.pop("pending_message_user", None)
        context.user_data.pop("pending_message_text", None)
        return

    try:
        await context.bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
        )
    except Exception as exc:
        logging.exception("Foydalanuvchiga xabar yuborishda xato: %s", exc)
        await query.edit_message_text(
            "❌ Xabar yuborishda xatolik yuz berdi.",
            reply_markup=main_menu_keyboard(),
        )
        return

    admin_user = query.from_user
    await create_audit_log(
        admin_telegram_id=admin_user.id,
        admin_username=admin_user.username,
        action=f"Xabar yuborildi: {user.email}",
        target_user=user,
        details=message_text,
    )

    context.user_data.pop("pending_message_user", None)
    context.user_data.pop("pending_message_text", None)

    await query.edit_message_text(
        "✅ Xabar muvaffaqiyatli yuborildi.",
        reply_markup=main_menu_keyboard(),
    )


async def cancel_send_message(query, context: CallbackContext):
    context.user_data.pop("admin_state", None)
    context.user_data.pop("pending_message_user", None)
    context.user_data.pop("pending_message_text", None)

    await query.edit_message_text(
        "❌ Xabar yuborish bekor qilindi.",
        reply_markup=main_menu_keyboard(),
    )


async def search_term(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    if context.user_data.get("admin_state") == "message":
        if "pending_message_user" not in context.user_data:
            await update.message.reply_text(
                "❌ Foydalanuvchi tanlanmadi. Iltimos, admin menyuga qayting.",
                reply_markup=main_menu_keyboard(),
            )
        return ConversationHandler.END

        context.user_data["pending_message_text"] = text
        context.user_data.pop("admin_state", None)
        await update.message.reply_text(
            "📨 Xabar tayyor.",
            reply_markup=confirm_message_keyboard(),
        )
        return ConversationHandler.END
        if not user:
            await update.message.reply_text(
                "❌ Foydalanuvchi topilmadi.",
                reply_markup=back_to_main_keyboard(),
            )
            return

        login_count = await get_user_login_count(user)
        text = format_user_card(user, login_count, settings.ONLINE_THRESHOLD_MINUTES)
        await update.message.reply_text(
            text,
            reply_markup=user_action_keyboard(user.id, user.is_online, user.is_phone_verified),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "❌ Iltimos, admin menyusidan boshlang.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def search_cancel(update: Update, context: CallbackContext):
    context.user_data.pop("admin_state", None)
    context.user_data.pop("pending_message_user", None)
    context.user_data.pop("pending_message_text", None)

    await update.message.reply_text(
        "🔙 Amaliyot bekor qilindi.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END
