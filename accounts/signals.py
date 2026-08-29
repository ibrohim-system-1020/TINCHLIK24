import logging
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def ensure_main_admin(sender, **kwargs):
    """Create or update the main admin user after migrations.

    This avoids running DB queries during AppConfig.ready(). The handler is idempotent
    and avoids UNIQUE conflicts on `telefon`.
    """
    try:
        User = get_user_model()
        username = getattr(settings, "MAIN_ADMIN_USERNAME", "admin")
        password = getattr(settings, "MAIN_ADMIN_PASSWORD", None) or "Tinchlik admin"
        admin_phone = getattr(settings, "ADMIN_PHONE_NUMBER", None)

        # Try find existing user by username or email
        user = None
        try:
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.filter(email=username).first()
        except Exception:
            logger.exception("Error querying for existing admin user")
            return

        if user:
            changed = False
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            # Ensure password matches desired admin password
            try:
                if not user.check_password(password):
                    user.set_password(password)
                    changed = True
            except Exception:
                user.set_password(password)
                changed = True

            # Only set telefon if it's not used by another user
            if admin_phone:
                from accounts.models import User as LocalUser

                conflict = LocalUser.objects.filter(telefon=admin_phone).exclude(pk=user.pk).exists()
                if not conflict and user.telefon != admin_phone:
                    user.telefon = admin_phone
                    changed = True

            if changed:
                try:
                    user.save()
                    logger.info("Updated main admin user '%s'", username)
                except Exception:
                    logger.exception("Failed to update main admin user")
            return

        # Create new admin user safely
        telefon_to_set = None
        if admin_phone:
            from accounts.models import User as LocalUser

            if not LocalUser.objects.filter(telefon=admin_phone).exists():
                telefon_to_set = admin_phone

        try:
            user = User.objects.create_user(
                email=username,
                password=password,
                first_name="Admin",
                last_name="",
                telefon=telefon_to_set,
                is_active=True,
            )
            user.username = username
            user.is_staff = True
            user.is_superuser = True
            user.save()
            logger.info("Created main admin user '%s' via post_migrate", username)
        except Exception:
            logger.exception("Failed creating main admin user in post_migrate")

    except Exception:
        logger.exception("Unexpected error in ensure_main_admin signal handler")
