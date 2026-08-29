from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
import logging

from .forms import RegisterForm, VerifyCodeForm, normalize_email, normalize_phone
from .models import LoginHistory


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


@login_required
def delete_account_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = request.user
    posted_user_id = request.POST.get("user_id")
    if posted_user_id is not None and str(posted_user_id) != str(user.pk):
        messages.error(
            request,
            "Siz faqat o'zingizning hisobingizni o'chira olasiz.",
        )
        return redirect("accounts:security")

    if user.is_superuser or getattr(user, "is_admin", False):
        messages.error(
            request,
            "Administrator hisobini bu yerdan ochirish mumkin emas.",
        )
        return redirect("accounts:security")

    provided_password = request.POST.get("password", "")
    if not user.check_password(provided_password):
        messages.error(
            request,
            "Parol xato kiritildi. Hisob ochirilmadi.",
        )
        return redirect("accounts:security")

    user_id = user.pk

    for session in Session.objects.iterator():
        data = session.get_decoded()
        if data.get("_auth_user_id") == str(user_id):
            session.delete()

    user.delete()
    request.session.flush()

    response = redirect("home")
    response.set_cookie(
        "account_deletion_success",
        "1",
        max_age=60,
        httponly=True,
        samesite="Lax",
    )
    return response


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


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        post_data = request.POST.copy()

        if "terms" in post_data and "agree_terms" not in post_data:
            post_data["agree_terms"] = "on"

        form = RegisterForm(post_data)

        if form.is_valid():
            email = normalize_email(form.cleaned_data["email"])
            telefon = normalize_phone(form.cleaned_data["telefon"])

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email,
                        password=form.cleaned_data["password1"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                        telefon=telefon,
                        is_phone_verified=True,
                        registered_via=User.RegisteredVia.SITE,
                    )
                    user.email_verified = True
                    user.save(update_fields=["email_verified"])
                    login(request, user)
                    LoginHistory.objects.create(user=user, ip_address=_client_ip(request))
            except IntegrityError:
                logger.exception("Registration failed while creating user")
                messages.error(
                    request,
                    "❌ Bu email yoki telefon raqam allaqachon ro'yxatdan o'tgan.",
                )
                _store_registration_data(request, form)
                return redirect("accounts:register")

            messages.success(request, "✅ Ro'yxatdan o'tdingiz va tizimga kirdingiz!")
            return redirect("home")

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
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

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

            return redirect("home")

        messages.error(
            request,
            "❌ Email yoki parol noto'g'ri.",
        )

        return redirect("/register/?tab=login")

    return redirect("/register/?tab=login")




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