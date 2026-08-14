import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Email asosida foydalanuvchi yaratadigan manager (username shart emas)."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email kiritilishi shart")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_phone_verified", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Loyihaning asosiy foydalanuvchi modeli.
    username maydoni saqlanadi (Django admin bilan mos bo'lishi uchun),
    lekin kirish (login) email orqali amalga oshiriladi.
    """

    class RegisteredVia(models.TextChoices):
        SITE = "site", "Sayt orqali (telefon tasdiqlash bilan)"
        TELEGRAM = "telegram", "Telegram orqali"

    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True)
    telefon = models.CharField(max_length=20, unique=True, null=True, blank=True)

    is_phone_verified = models.BooleanField(default=False)
    registered_via = models.CharField(
        max_length=10, choices=RegisteredVia.choices, default=RegisteredVia.SITE
    )

    # --- Telegram bilan bog'liq maydonlar ---
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=150, blank=True, null=True)
    telegram_photo_url = models.URLField(blank=True, null=True)

    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            base = (self.email.split("@")[0] if self.email else f"user{uuid.uuid4().hex[:8]}")
            candidate = base
            i = 1
            while User.objects.filter(username=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}{i}"
            self.username = candidate

        if self.telegram_id is not None:
            admin_ids = getattr(settings, "ADMIN_TELEGRAM_IDS", [])
            if int(self.telegram_id) in admin_ids:
                self.is_staff = True
                self.is_superuser = True
                self.is_active = True

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        threshold = timezone.now() - timedelta(
            minutes=getattr(settings, "ONLINE_THRESHOLD_MINUTES", 5)
        )
        return self.last_seen >= threshold

    @property
    def is_admin(self):
        telegram_id = getattr(self, "telegram_id", None)
        if self.is_staff or self.is_superuser:
            return True
        if telegram_id is None:
            return False
        return int(telegram_id) in getattr(settings, "ADMIN_TELEGRAM_IDS", [])

    @property
    def profile_photo_url(self):
        """Telegram orqali ro'yxatdan o'tgan bo'lsa, telegramdagi profil rasmi ko'rsatiladi."""
        if self.telegram_photo_url:
            return self.telegram_photo_url
        return None

    def __str__(self):
        return self.full_name or self.email


class PendingRegistration(models.Model):
    """
    Sayt orqali ro'yxatdan o'tish boshlanganda, lekin telefon/Telegram
    orqali hali tasdiqlanmagan holatdagi vaqtinchalik ma'lumotlar.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    first_name = models.CharField("Ism", max_length=150)
    last_name = models.CharField("Familiya", max_length=150)
    email = models.EmailField()
    password_hash = models.CharField(max_length=255)
    telefon = models.CharField(max_length=20)

    telegram_id = models.BigIntegerField(null=True, blank=True)
    telegram_username = models.CharField(max_length=150, blank=True, null=True)
    telegram_photo_url = models.URLField(blank=True, null=True)

    telegram_gateway_request_id = models.CharField(max_length=255, blank=True, null=True)
    telegram_gateway_requested_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)

    code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def generate_code(self):
        self.code = f"{random.randint(0, 999999):06d}"
        self.code_created_at = timezone.now()
        self.save(update_fields=["code", "code_created_at"])
        return self.code

    def code_is_valid(self, submitted_code):
        if not self.code or not self.code_created_at:
            return False
        ttl = timedelta(minutes=getattr(settings, "VERIFICATION_CODE_TTL_MINUTES", 5))
        if timezone.now() - self.code_created_at > ttl:
            return False
        return submitted_code.strip() == self.code

    def gateway_send_cooldown_remaining(self):
        if not self.telegram_gateway_requested_at:
            return 0
        cooldown = getattr(settings, "TELEGRAM_GATEWAY_RESEND_COOLDOWN_SECONDS", 60)
        elapsed = (timezone.now() - self.telegram_gateway_requested_at).total_seconds()
        return max(0, int(cooldown - elapsed))

    def gateway_code_is_expired(self):
        if not self.telegram_gateway_requested_at:
            return True
        ttl = getattr(settings, "TELEGRAM_GATEWAY_CODE_TTL_SECONDS", 300)
        return (timezone.now() - self.telegram_gateway_requested_at).total_seconds() > ttl

    def is_expired(self):
        expire_minutes = getattr(settings, "PENDING_REGISTRATION_EXPIRE_MINUTES", 30)
        if not self.created_at:
            return False
        return (timezone.now() - self.created_at).total_seconds() > (expire_minutes * 60)

    def reset_verification(self):
        self.telegram_gateway_request_id = None
        self.telegram_gateway_requested_at = None
        self.phone_verified_at = None
        self.code = None
        self.code_created_at = None
        self.save(update_fields=[
            "telegram_gateway_request_id",
            "telegram_gateway_requested_at",
            "phone_verified_at",
            "code",
            "code_created_at",
        ])

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.telefon})"


class LoginHistory(models.Model):
    """Har bir kirishni qayd qilib boradi (admin bot 'qachon kirgan' ma'lumoti uchun)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_history")
    logged_in_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-logged_in_at"]
        verbose_name = "Kirish tarixi"
        verbose_name_plural = "Kirishlar tarixi"

    def __str__(self):
        return f"{self.user} - {self.logged_in_at:%Y-%m-%d %H:%M}"


class AdminAuditLog(models.Model):
    """Admin bot orqali amalga oshirilgan muhim harakatlar uchun audit yozuvi."""

    admin_telegram_id = models.BigIntegerField()
    admin_username = models.CharField(max_length=150, blank=True, null=True)
    action = models.CharField(max_length=120)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_audit_logs",
    )
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Admin Audit Log"
        verbose_name_plural = "Admin Audit Logs"

    def __str__(self):
        return f"{self.action} by {self.admin_username or self.admin_telegram_id}"


class TelegramOutMessage(models.Model):
    """Track outgoing Telegram messages sent by the bot.

    This is used to:
    - mark normal (temporary) messages so they can be deleted when the bot sends a new normal message
    - mark verification_code messages so they are preserved for 24 hours and then deleted by a periodic job
    """

    MESSAGE_TYPE_CHOICES = [
        ("temporary", "Temporary"),
        ("verification_code", "Verification Code"),
    ]

    chat_id = models.BigIntegerField(db_index=True)
    message_id = models.IntegerField()

    # Optional link to local user or pending registration token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="telegram_out_messages",
    )
    pending_token = models.UUIDField(null=True, blank=True)

    message_type = models.CharField(max_length=32, choices=MESSAGE_TYPE_CHOICES, default="temporary")
    sent_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [models.Index(fields=["chat_id", "message_type"])]

    def __str__(self):
        return f"TelegramOutMessage {self.chat_id}:{self.message_id} ({self.message_type})"