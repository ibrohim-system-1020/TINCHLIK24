from django.conf import settings


def is_admin_telegram_id(telegram_id: int) -> bool:
    """Check if a Telegram ID is in the configured admin whitelist."""
    if telegram_id is None:
        return False
    return int(telegram_id) in getattr(settings, "ADMIN_TELEGRAM_IDS", [])


def format_user_card(user, login_count: int, online_threshold_minutes: int) -> str:
    online_status = "🟢 Online" if user.is_online else "⚫ Offline"
    verified_status = "✅ Tasdiqlangan" if user.is_phone_verified else "⚠️ Tasdiqlanmagan"
    telegram_line = "Telegram ulangan" if user.telegram_id else "Telegram ulanmagan"

    lines = [
        "━━━━━━━━━━━━━━━━",
        "👤 FOYDALANUVCHI",
        "━━━━━━━━━━━━━━━━",
        f"ID: {user.id}",
        f"Ism: {user.first_name or '-'}",
        f"Familiya: {user.last_name or '-'}",
        f"Email: {user.email}",
        f"Telefon: {user.telefon or '-'}",
        f"Telegram: @{user.telegram_username}" if user.telegram_username else "Telegram: -",
        f"Registered via: {user.registered_via.upper()}",
        f"Ro'yxatdan o'tgan: {user.date_joined.strftime('%d.%m.%Y %H:%M')}",
        f"Oxirgi login: {user.last_login.strftime('%d.%m.%Y %H:%M') if user.last_login else 'Hali mavjud emas'}",
        f"Oxirgi faollik: {user.last_seen.strftime('%d.%m.%Y %H:%M') if user.last_seen else 'Mavjud emas'}",
        f"Holat: {online_status}",
        f"Verification: {verified_status}",
        f"Login count: {login_count}",
        "━━━━━━━━━━━━━━━━",
    ]
    return "\n".join(lines)
