import re

from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import PendingRegistration, User


PHONE_NORMALIZATION_PATTERN = re.compile(r"[^\d+]+")


def normalize_phone(phone):
    if not phone:
        return None

    value = str(phone).strip()
    value = PHONE_NORMALIZATION_PATTERN.sub("", value)

    if value.startswith("+"):
        value = value[1:]

    if value.startswith("998") and len(value) == 12:
        return f"+{value}"

    if len(value) == 9:
        return f"+998{value}"

    if len(value) == 10 and value.startswith("0"):
        return f"+998{value[1:]}"

    return None


def normalize_email(email):
    if not email:
        return None
    return str(email).strip().lower()



class RegisterForm(forms.Form):
    first_name = forms.CharField(
        label="Ism", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ismingiz", "class": "form-input"}),
    )
    last_name = forms.CharField(
        label="Familiya", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Familiyangiz", "class": "form-input"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "email@misol.com", "class": "form-input"}),
    )
    telefon = forms.CharField(
        label="Telefon raqam", max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "+998901234567", "class": "form-input"}),
    )
    password1 = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={"placeholder": "Parol", "class": "form-input"}),
    )
    password2 = forms.CharField(
        label="Parolni qayta yozing",
        widget=forms.PasswordInput(attrs={"placeholder": "Parolni takrorlang", "class": "form-input"}),
    )
    agree_terms = forms.BooleanField(
        label="Shartlarga roziman",
        error_messages={"required": "Davom etish uchun shartlarga rozilik bildirishingiz kerak"},
    )

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if not email:
            raise ValidationError("Email manzilingizni kiriting.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")
        return email

    def clean_telefon(self):
        telefon = normalize_phone(self.cleaned_data["telefon"])
        if not telefon:
            raise ValidationError(
                "Telefon raqam formatini to'g'ri kiriting. Masalan: +998901234567"
            )
        if User.objects.filter(telefon=telefon).exists():
            raise ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")
        return telefon

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Parollar bir-biriga mos emas.")
        if p1:
            try:
                password_validation.validate_password(p1)
            except ValidationError as e:
                self.add_error("password1", e)
        return cleaned


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        label="Tasdiqlash kodi", max_length=6,
        widget=forms.TextInput(attrs={"placeholder": "123456", "class": "form-input", "autofocus": True}),
    )


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "email@misol.com", "class": "form-input"}),
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={"placeholder": "Parol", "class": "form-input"}),
    )