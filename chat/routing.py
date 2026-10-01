from django.urls import re_path

from .consumers import ChatConsumer, DirectChatConsumer

websocket_urlpatterns = [
    re_path(r"^ws/chat/direct/$", DirectChatConsumer.as_asgi()),
    re_path(r"^ws/chat/$", ChatConsumer.as_asgi()),
]
