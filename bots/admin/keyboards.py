try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
except Exception:
    class InlineKeyboardButton:
        def __init__(self, text, callback_data=None):
            self.text = text
            self.callback_data = callback_data

    class InlineKeyboardMarkup:
        def __init__(self, buttons):
            self.inline_keyboard = buttons


def normal_user_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika", callback_data="user:stats")],
        [InlineKeyboardButton("🏆 Reytinglar", callback_data="user:ranking")],
        [InlineKeyboardButton("🟢 Online", callback_data="user:online")],
        [InlineKeyboardButton("👤 Mening profilim", callback_data="user:profile")],
        [InlineKeyboardButton("🚪 Chiqish", callback_data="user:logout")],
    ])


def main_admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin:dashboard")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin:users")],
        [InlineKeyboardButton("🔎 Qidirish", callback_data="admin:search")],
        [InlineKeyboardButton("🟢 Online", callback_data="admin:online")],
        [InlineKeyboardButton("🏆 Reytinglar", callback_data="admin:ranking")],
        [InlineKeyboardButton("📈 Statistika", callback_data="admin:stats")],
        [InlineKeyboardButton("📝 So'rovlar", callback_data="admin:requests")],
        [InlineKeyboardButton("🔁 Qayta kirishlar", callback_data="admin:reentries")],
        [InlineKeyboardButton("🔐 Xavfsizlik", callback_data="admin:security")],
        [InlineKeyboardButton("🧾 Audit log", callback_data="admin:audit")],
        [InlineKeyboardButton("👮 Adminlar", callback_data="admin:admins")],
        [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin:settings")],
        [InlineKeyboardButton("🚪 Chiqish", callback_data="admin:logout")],
    ])


def main_menu_keyboard():
    return main_admin_menu_keyboard()


def users_pagination_keyboard(page: int, total_pages: int):
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin:users:page:{page-1}"))
    row.append(InlineKeyboardButton(f"{page} / {total_pages}", callback_data="admin:noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin:users:page:{page+1}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:main")])
    return InlineKeyboardMarkup(buttons)


def users_list_keyboard(users):
    buttons = []
    for user in users:
        buttons.append([
            InlineKeyboardButton(
                f"{user.id}. {user.first_name or '-'} {user.last_name or '-'}",
                callback_data=f"admin:user:view:{user.id}",
            )
        ])
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:main")])
    return InlineKeyboardMarkup(buttons)


def user_action_keyboard(user_id: int, is_online: bool, is_verified: bool):
    buttons = [
        [InlineKeyboardButton("🕘 Login tarixi", callback_data=f"admin:user:history:{user_id}" )],
        [InlineKeyboardButton("📨 Xabar yuborish", callback_data=f"admin:user:message:{user_id}" )],
    ]
    if not is_verified:
        buttons.insert(0, [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin:user:verify:{user_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:users")])
    return InlineKeyboardMarkup(buttons)


def confirm_message_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yuborish", callback_data="admin:message:confirm")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin:message:cancel")],
    ])


def back_to_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="admin:main")],
        [InlineKeyboardButton("🏠 Admin menu", callback_data="admin:main")],
    ])
