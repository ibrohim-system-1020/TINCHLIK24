from datetime import timedelta

from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone

from adminpanel.models import Announcement
from chat.models import ChatPresence
from market.models import Listing


def home(request):
    if request.COOKIES.get("account_deletion_success") == "1":
        messages.success(request, "Hisobingiz muvaffaqiyatli olib tashlandi.")

    latest_listings = (
        Listing.objects.filter(status=Listing.STATUS_APPROVED)
        .select_related("seller")
        .prefetch_related("images")
        .order_by("-created_at")[:6]
    )

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

        user_listings = request.user.listings.order_by("-created_at")[:3]

        response = render(
            request,
            "home.html",
            {
                "user": request.user,
                "online_users": online_users_data,
                "announcements": Announcement.objects.filter(
                    target_all=True,
                    target_online_only=False,
                ).order_by("-created_at")[:4],
                "latest_listings": latest_listings,
                "user_listings": user_listings,
            },
        )
        if request.COOKIES.get("account_deletion_success") == "1":
            response.delete_cookie("account_deletion_success")
        return response

    response = render(
        request,
        "home.html",
        {
            "latest_listings": latest_listings,
            "announcements": Announcement.objects.filter(
                target_all=True,
                target_online_only=False,
            ).order_by("-created_at")[:4],
        },
    )
    if request.COOKIES.get("account_deletion_success") == "1":
        response.delete_cookie("account_deletion_success")
    return response


def register(request):
    return render(request, 'base.html')
    
