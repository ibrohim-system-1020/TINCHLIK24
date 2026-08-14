from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from chat.models import ChatPresence


def home(request):
    if request.user.is_authenticated:
        online_users = ChatPresence.objects.filter(
            is_active=True,
            last_seen__gte=timezone.now() - timedelta(minutes=5),
        ).select_related("user").order_by("-last_seen", "user__first_name", "user__email")

        online_users_data = []
        for presence in online_users:
            user = presence.user
            online_users_data.append({
                "id": user.id,
                "name": user.get_full_name() or user.email,
                "avatar": user.profile_photo_url,
                "email": user.email,
            })

        return render(
            request,
            "home.html",
            {
                "online_users": online_users_data,
                "news_items": [],
            },
        )

    return render(request, "home.html")


def register(request):
    return render(request, 'base.html')
    
