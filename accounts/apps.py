from django.apps import AppConfig
import logging


logger = logging.getLogger(__name__)
 
 
class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Hisoblar (Accounts)"
    def ready(self):
        # Register signal handlers. Avoid performing database queries here.
        try:
            import accounts.signals  # noqa: F401
        except Exception:
            logger.exception("Failed importing accounts.signals in ready(); signals may not be registered")