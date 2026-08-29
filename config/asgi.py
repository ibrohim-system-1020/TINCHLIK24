"""
ASGI config for config project.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application

# Avval Django to'liq ishga tushadi
django_asgi_app = get_asgi_application()

# Django apps tayyor bo'lgandan keyin models/routing import qilinadi
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.sessions import SessionMiddlewareStack

import chat.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            SessionMiddlewareStack(
                AuthMiddlewareStack(
                    URLRouter(chat.routing.websocket_urlpatterns)
                )
            )
        ),
    }
)
