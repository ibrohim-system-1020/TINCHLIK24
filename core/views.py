from datetime import timedelta

from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone

from accounts.models import LoginHistory
from chat.models import ChatPresence
from market.models import Listing


def home(request):
    if request.COOKIES.get("account_deletion_success") == "1":
        messages.success(request, "Hisobingiz muvaffaqiyatli olib tashlandi.")

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

        recent_logins = list(request.user.login_history.all()[:5])
        recent_requests = []
        for index, login in enumerate(recent_logins):
            if index == 0:
                status = "Yangi"
                status_class = "new"
            elif index % 2 == 0:
                status = "Ko‘rib chiqilmoqda"
                status_class = "pending"
            else:
                status = "Hal qilindi"
                status_class = "done"

            recent_requests.append({
                "title": f"Kirish {index + 1}",
                "date": login.logged_in_at,
                "status": status,
                "status_class": status_class,
                "detail_url": "/profile/",
            })

        total_requests = len(recent_requests)
        in_progress = sum(1 for item in recent_requests if item["status"] == "Ko‘rib chiqilmoqda")
        resolved = sum(1 for item in recent_requests if item["status"] == "Hal qilindi")
        rejected = sum(1 for item in recent_requests if item["status"] == "Rad etildi")

        news_items = [
            {
                "title": "Suv ta'minoti rejalashtirildi",
                "summary": "Bashorat bo'yicha suv uzatish jadvali bugun soat 15:00 da yangilanadi.",
                "created_at": timezone.now() - timedelta(days=1),
            },
            {
                "title": "Elektr ishlari bo'yicha ogohlantirish",
                "summary": "Mahalla ichidagi elektr ta'minoti ishlari bo'yicha xabarlar e'lon qilindi.",
                "created_at": timezone.now() - timedelta(days=2),
            },
            {
                "title": "Mahalla yig'ilishi",
                "summary": "Hamkorlik va xavfsizlik bo'yicha uchrashuv chorshanba kuni soat 18:00 da bo'lib o'tadi.",
                "created_at": timezone.now() - timedelta(days=3),
            },
        ]

        latest_listings = (
            Listing.objects.filter(status=Listing.STATUS_APPROVED)
            .select_related("seller")
            .prefetch_related("images")
            .order_by("-created_at")[:6]
        )

        user_listings = request.user.listings.order_by("-created_at")[:3]

        response = render(
            request,
            "home.html",
            {
                "user": request.user,
                "online_users": online_users_data,
                "news_items": news_items,
                "recent_requests": recent_requests,
                "latest_listings": latest_listings,
                "user_listings": user_listings,
                "dashboard_stats": {
                    "total": total_requests or 4,
                    "in_progress": in_progress or 2,
                    "resolved": resolved or 2,
                    "rejected": rejected or 0,
                },
            },
        )
        if request.COOKIES.get("account_deletion_success") == "1":
            response.delete_cookie("account_deletion_success")
        return response

    response = render(request, "home.html")
    if request.COOKIES.get("account_deletion_success") == "1":
        response.delete_cookie("account_deletion_success")
    return response


def register(request):
    return render(request, 'base.html')
    
