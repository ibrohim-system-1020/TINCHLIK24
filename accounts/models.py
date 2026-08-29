import random
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import check_password, make_password
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
        user._sync_admin_flags()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_phone_verified", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Loyihaning asosiy foydalanuvchi modeli.
    username maydoni saqlanadi (Django admin bilan mos bo'lishi uchun),
    lekin kirish (login) email orqali amalga oshiriladi.
    """

    @staticmethod
    def _normalize_phone_for_admin_check(phone_value):
        from accounts.forms import normalize_phone

        normalized = normalize_phone(phone_value)
        if not normalized:
            return ""
        return normalized

    def _sync_admin_flags(self):
        normalized_phone = self._normalize_phone_for_admin_check(self.telefon)
        admin_phone = self._normalize_phone_for_admin_check(
            getattr(settings, "ADMIN_PHONE_NUMBER", "+998991649848")
        )
        is_admin = bool(admin_phone) and normalized_phone == admin_phone
        # Only grant admin flags when phone matches configured admin phone.
        # Do not revoke existing admin flags here to avoid overwriting programmatic
        # changes (for example when an admin was set via management command).
        if is_admin:
            self.is_staff = True
            self.is_superuser = True
        return is_admin

    class RegisteredVia(models.TextChoices):
        SITE = "site", "Sayt orqali (telefon tasdiqlash bilan)"
        TELEGRAM = "telegram", "Telegram orqali"

    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
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

        self.telefon = self._normalize_phone_for_admin_check(self.telefon) or self.telefon
        self._sync_admin_flags()

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
        return self._sync_admin_flags()

    @property
    def profile_photo_url(self):
        """Telegram orqali ro'yxatdan o'tgan bo'lsa, telegramdagi profil rasmi ko'rsatiladi."""
        if self.telegram_photo_url:
            return self.telegram_photo_url
        return None

    def __str__(self):
        return self.full_name or self.email


class PendingRegistration(models.Model):
    """Telegram link verification flow for secure registration."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        TELEGRAM_LINKED = "telegram_linked", "Telegram linked"
        VERIFIED = "verified", "Verified"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    verification_token = models.CharField(max_length=128, null=True, blank=True, unique=True)
    verification_token_hash = models.CharField(max_length=255, null=True, blank=True)

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
    email_sent_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def generate_verification_token(self):
        token = secrets.token_urlsafe(32)
        self.verification_token = token
        self.verification_token_hash = make_password(token)
        expire_minutes = getattr(settings, "EMAIL_VERIFICATION_EXPIRE_MINUTES", 30)
        self.expires_at = timezone.now() + timedelta(minutes=expire_minutes)
        self.status = self.Status.PENDING
        return token

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = uuid.uuid4()
        if not self.status:
            self.status = self.Status.PENDING
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        # Ensure a verification token exists for pending registrations only
        # when status is not explicitly set to VERIFIED or COMPLETED.
        if not self.verification_token and (not self.status or self.status == self.Status.PENDING):
            self.generate_verification_token()
        if self.verification_token and not self.verification_token_hash:
            self.verification_token_hash = make_password(self.verification_token)
        if self.verification_token_hash and self.verification_token and self.verification_token_hash.startswith("!") is False and not self.verification_token_hash.startswith("pbkdf2"):
            self.verification_token_hash = make_password(self.verification_token)
        super().save(*args, **kwargs)

    def verify_token(self, submitted_token):
        if not submitted_token or not self.verification_token_hash:
            return False
        return check_password(submitted_token, self.verification_token_hash)

    def mark_verified(self, telegram_id=None, telegram_username=None, telegram_photo_url=None):
        self.telegram_id = telegram_id or self.telegram_id
        self.telegram_username = telegram_username or self.telegram_username
        self.telegram_photo_url = telegram_photo_url or self.telegram_photo_url
        self.status = self.Status.VERIFIED
        self.phone_verified_at = timezone.now()
        self.verified_at = timezone.now()
        self.save(update_fields=[
            "telegram_id",
            "telegram_username",
            "telegram_photo_url",
            "status",
            "phone_verified_at",
            "verified_at",
        ])
        return True

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.is_completed = True
        self.used_at = timezone.now()
        self.save(update_fields=["status", "is_completed", "used_at"])

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

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED and self.verified_at is not None

    @property
    def is_used(self):
        return self.status == self.Status.COMPLETED or self.used_at is not None

    @property
    def can_be_completed(self):
        return self.is_verified and not self.is_used and not self.is_expired()

    def is_expired(self):
        if self.status in {self.Status.COMPLETED, self.Status.CANCELLED}:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        expire_minutes = getattr(settings, "PENDING_REGISTRATION_EXPIRE_MINUTES", 30)
        if not self.created_at:
            return False
        return (timezone.now() - self.created_at).total_seconds() > (expire_minutes * 60)

    def reset_verification(self):
        self.telegram_gateway_request_id = None
        self.telegram_gateway_requested_at = None
        self.email_sent_at = None
        self.phone_verified_at = None
        self.verified_at = None
        self.status = self.Status.PENDING
        self.code = None
        self.code_created_at = None
        expire_minutes = getattr(settings, "EMAIL_VERIFICATION_EXPIRE_MINUTES", 30)
        self.expires_at = timezone.now() + timedelta(minutes=expire_minutes)
        self.generate_verification_token()
        self.save(update_fields=[
            "telegram_gateway_request_id",
            "telegram_gateway_requested_at",
            "phone_verified_at",
            "verified_at",
            "status",
            "code",
            "code_created_at",
            "expires_at",
            "verification_token",
            "verification_token_hash",
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