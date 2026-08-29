from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def send_verification_email(pending, request=None):
    site_url = getattr(settings, "SITE_URL", None) or getattr(settings, "PUBLIC_BASE_URL", None)
    if not site_url and request is not None:
        site_url = request.build_absolute_uri("/").rstrip("/")
    if not site_url:
        site_url = "https://tinchlik24.uz"

    token = pending.verification_token
    verify_url = f"{site_url}/accounts/verify-email/{token}/"

    subject = "TINCHLIK — Email manzilingizni tasdiqlang"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "TINCHLIK <noreply@localhost>")

    context = {
        "pending": pending,
        "verify_url": verify_url,
        "site_name": getattr(settings, "SITE_NAME", "TINCHLIK"),
        "expire_minutes": getattr(settings, "EMAIL_VERIFICATION_EXPIRE_MINUTES", 30),
    }

    text_body = render_to_string("accounts/email_verification.txt", context)
    html_body = render_to_string("accounts/email_verification.html", context)

    msg = EmailMultiAlternatives(subject, text_body, from_email, [pending.email])
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send()
    except Exception:
        # log and let caller handle errors; we avoid raising to not crash registration flow
        import logging

        logger = logging.getLogger(__name__)
        logger.exception("Failed to send verification email to %s", pending.email)
        return False

    pending.email_sent_at = timezone.now()
    pending.save(update_fields=["email_sent_at"])
    return True
