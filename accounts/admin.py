from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AdminAuditLog, User, LoginHistory, PendingRegistration


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "first_name", "last_name", "telefon", "registered_via", "is_phone_verified", "is_online", "last_seen")
    list_filter = ("registered_via", "is_phone_verified", "is_staff")
    search_fields = ("email", "first_name", "last_name", "telefon", "telegram_username")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Shaxsiy ma'lumot", {"fields": ("first_name", "last_name", "telefon")}),
        ("Telegram", {"fields": ("telegram_id", "telegram_username", "telegram_photo_url")}),
        ("Holat", {"fields": ("registered_via", "is_phone_verified", "last_seen", "is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "logged_in_at", "ip_address")
    list_filter = ("logged_in_at",)


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "telefon", "created_at", "is_completed")


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("admin_username", "admin_telegram_id", "action", "target_user", "created_at")
    search_fields = ("admin_username", "action", "details", "target_user__email", "target_user__telefon")
    list_filter = ("action", "created_at")