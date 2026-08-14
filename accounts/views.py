from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import logging

from .forms import RegisterForm, VerifyCodeForm, normalize_email, normalize_phone
from .models import LoginHistory, PendingRegistration
from .services.telegram_gateway import (
    TelegramGatewayError,
    TelegramGatewaySendError,
    TelegramGatewayUnavailable,
    check_verification_status,
    send_verification_message,
)


User = get_user_model()

logger = logging.getLogger(__name__)


@login_required
def security_view(request):
    return render(
        request,
        "accounts/security.html",
        {
            "profile_user": request.user,
        },
    )


def _store_registration_data(request, form):
    request.session["registration_form_data"] = {
        "first_name": form.data.get("first_name", ""),
        "last_name": form.data.get("last_name", ""),
        "email": form.data.get("email", ""),
        "telefon": form.data.get("telefon", ""),
    }
    request.session.modified = True


def _get_registration_data(request):
    return request.session.pop("registration_form_data", {})


def _find_reusable_pending(email, telefon):
    pending_qs = PendingRegistration.objects.filter(
        is_completed=False,
    ).filter(
        Q(email=email) | Q(telefon=telefon)
    ).order_by("-created_at")

    if not pending_qs.exists():
        return None

    pending = pending_qs.first()
    if pending.is_expired():
        pending_qs.delete()
        return None

    return pending


def _prepare_pending_registration(
    email,
    telefon,
    first_name,
    last_name,
    password_hash,
):
    pending = _find_reusable_pending(email, telefon)
    if pending is None:
        return PendingRegistration.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            telefon=telefon,
            password_hash=password_hash,
        )

    pending.first_name = first_name
    pending.last_name = last_name
    pending.email = email
    pending.telefon = telefon
    pending.password_hash = password_hash
    pending.reset_verification()
    pending.save()
    return pending


def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        post_data = request.POST.copy()

        if "terms" in post_data and "agree_terms" not in post_data:
            post_data["agree_terms"] = "on"

        form = RegisterForm(post_data)

        if form.is_valid():
            email = normalize_email(form.cleaned_data["email"])
            telefon = normalize_phone(form.cleaned_data["telefon"])
            password_hash = make_password(form.cleaned_data["password1"])

            try:
                with transaction.atomic():
                    pending = _prepare_pending_registration(
                        email=email,
                        telefon=telefon,
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                        password_hash=password_hash,
                    )
            except Exception:
                messages.error(
                    request,
                    "❌ Ichki tizim xatosi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
                )
                _store_registration_data(request, form)
                return redirect("accounts:register")

            try:
                request_id = send_verification_message(pending.telefon)
            except (TelegramGatewayUnavailable, TelegramGatewaySendError, TelegramGatewayError) as e:
                # If gateway sending fails, fallback to manual bot deep-link flow.
                logger.exception("Telegram gateway failed, falling back to bot deep link: %s", e)

                bot_username = getattr(settings, "USER_BOT_USERNAME", None)
                if bot_username:
                    deep_link = f"https://t.me/{bot_username}?start=reg_{pending.token}"
                    messages.info(
                        request,
                        "✅ Telegram orqali yuborib bo'lmadi, lekin davom ettirish uchun quyidagi tugmaga bosing.",
                    )
                    messages.info(request, deep_link)
                    return redirect(
                        "accounts:register_telegram_link",
                        token=pending.token,
                    )

                # If no bot username configured, show original error
                messages.error(
                    request,
                    f"❌ {str(e)}",
                )
                _store_registration_data(request, form)
                return redirect("accounts:register")

            pending.telegram_gateway_request_id = request_id
            pending.telegram_gateway_requested_at = timezone.now()
            pending.save(update_fields=[
                "telegram_gateway_request_id",
                "telegram_gateway_requested_at",
            ])

            return redirect(
                "accounts:register_telegram_link",
                token=pending.token,
            )

        _store_registration_data(request, form)
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    error_messages.append(str(error))
                else:
                    field_name = form.fields[field].label or field
                    error_messages.append(f"{field_name}: {error}")

        unique_errors = list(dict.fromkeys(error_messages))
        joined_errors = " | ".join(unique_errors)

        messages.error(
            request,
            f"❌ Ro'yxatdan o'tishda xatolik: {joined_errors}",
        )

        return redirect("accounts:register")

    registration_data = _get_registration_data(request)
    return render(
        request,
        "accounts/register.html",
        {
            "registration_data": registration_data,
            "bot_username": settings.USER_BOT_USERNAME,
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        email_value = (
            request.POST.get("email")
            or request.POST.get("username")
        )

        password = request.POST.get("password", "")

        if not email_value or not password:
            messages.error(
                request,
                "❌ Email va parolni kiriting.",
            )

            return redirect("/register/?tab=login")

        user = authenticate(
            request,
            username=email_value.strip().lower(),
            password=password,
        )

        if user is not None:
            login(request, user)

            LoginHistory.objects.create(
                user=user,
                ip_address=_client_ip(request),
            )

            messages.success(
                request,
                "✅ Tizimga muvaffaqiyatli kirdingiz!",
            )

            return redirect("accounts:profile")

        messages.error(
            request,
            "❌ Email yoki parol noto'g'ri.",
        )

        return redirect("/register/?tab=login")

    return redirect("/register/?tab=login")


def register_telegram_link_view(request, token):
    pending = get_object_or_404(
        PendingRegistration,
        token=token,
        is_completed=False,
    )

    cooldown_remaining = pending.gateway_send_cooldown_remaining()
    code_expired = pending.gateway_code_is_expired()

    bot_username = getattr(settings, "USER_BOT_USERNAME", None)
    deep_link = None
    if bot_username:
        deep_link = f"https://t.me/{bot_username}?start=reg_{pending.token}"

    return render(
        request,
        "accounts/register_telegram_wait.html",
        {
            "pending": pending,
            "cooldown_remaining": cooldown_remaining,
            "code_expired": code_expired,
            "deep_link": deep_link,
        },
    )


def register_telegram_wait(request):
    bot_username = settings.USER_BOT_USERNAME

    deep_link = (
        f"https://t.me/{bot_username}?start=register"
    )

    return render(
        request,
        "accounts/register_telegram_wait.html",
        {
            "deep_link": deep_link,
        },
    )


def pending_status_api(request, token):
    pending = get_object_or_404(
        PendingRegistration,
        token=token,
        is_completed=False,
    )

    code_sent = bool(
        (pending.code and pending.telegram_id)
        or pending.telegram_gateway_request_id
    )

    return JsonResponse(
        {
            "code_sent": code_sent,
        }
    )


def verify_code_view(request, token):
    pending = get_object_or_404(
        PendingRegistration,
        token=token,
        is_completed=False,
    )

    if request.method != "POST":
        form = VerifyCodeForm()
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    form = VerifyCodeForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    code = form.cleaned_data["code"].strip()
    verified = False
    verification_error = None

    if pending.telegram_id and pending.code:
        if not pending.code_is_valid(code):
            verification_error = "Kod noto'g'ri yoki muddati o'tgan."
        elif User.objects.filter(telegram_id=pending.telegram_id).exists():
            verification_error = "Ushbu Telegram akkaunti boshqa TINCHLIK hisobiga allaqachon ulangan."
        else:
            verified = True
    elif pending.telegram_gateway_request_id:
        try:
            verified = check_verification_status(
                pending.telegram_gateway_request_id,
                code,
            )
        except TelegramGatewayUnavailable:
            verification_error = (
                "Telegram Gateway vaqtincha mavjud emas. Iltimos, birozdan so'ng qayta urinib ko'ring."
            )
        except TelegramGatewayError:
            verification_error = (
                "Tasdiqlash kodini tekshirishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."
            )
        else:
            if not verified:
                verification_error = "Kod noto'g'ri yoki muddati o'tgan."
    else:
        messages.error(
            request,
            "❌ Tasdiqlash so'rovi topilmadi. Iltimos ro'yxatdan qayta o'ting.",
        )
        return redirect("accounts:register")

    if verification_error:
        form.add_error("code", verification_error)
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    if not verified:
        form.add_error("code", "Kod noto'g'ri yoki muddati o'tgan.")
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    pending.phone_verified_at = timezone.now()
    pending.save(update_fields=["phone_verified_at"])

    conflict_errors = []
    if User.objects.filter(email=pending.email).exists():
        conflict_errors.append("Email allaqachon ro'yxatdan o'tgan.")
    if User.objects.filter(telefon=pending.telefon).exists():
        conflict_errors.append("Telefon raqam allaqachon ro'yxatdan o'tgan.")

    if conflict_errors:
        form.add_error(None, " | ".join(conflict_errors))
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    try:
        with transaction.atomic():
            user = User(
                first_name=pending.first_name,
                last_name=pending.last_name,
                email=pending.email,
                telefon=pending.telefon,
                is_phone_verified=True,
                registered_via=User.RegisteredVia.SITE,
                telegram_id=pending.telegram_id,
                telegram_username=pending.telegram_username,
                telegram_photo_url=pending.telegram_photo_url,
            )
            user.password = pending.password_hash
            user.save()
            pending.is_completed = True
            pending.save(update_fields=["is_completed"])
    except IntegrityError:
        form.add_error(None, "Hisob yaratishda raqobat yuz berdi. Iltimos, qayta urinib ko'ring.")
        return render(
            request,
            "accounts/register_telegram_wait.html",
            {
                "pending": pending,
                "cooldown_remaining": pending.gateway_send_cooldown_remaining(),
                "code_expired": pending.gateway_code_is_expired(),
                "form": form,
            },
        )

    login(request, user)
    LoginHistory.objects.create(
        user=user,
        ip_address=_client_ip(request),
    )

    messages.success(
        request,
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!",
    )

    return redirect("accounts:profile")


def logout_view(request):
    logout(request)

    return redirect("home")


@login_required
def profile_view(request):
    history = request.user.login_history.all()[:10]

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": request.user,
            "history": history,
            "is_admin": getattr(request.user, "is_admin", False),
        },
    )


def _client_ip(request):
    xff = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if xff:
        return xff.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR"
    )