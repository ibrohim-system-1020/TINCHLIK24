from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Count

from django.contrib.auth import get_user_model

from chat.models import ChatMessage
from market.models import Listing
from .models import Report, UserWarning, UserBan, UserMute, AdminActionLog


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff and u.is_superuser)(view_func)


@admin_required
def dashboard_view(request):
    User = get_user_model()
    total_users = User.objects.count()
    today = timezone.now().date()
    todays_users = User.objects.filter(date_joined__date=today).count()
    online_users = User.objects.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).count()
    blocked = UserBan.objects.count()
    spammed = UserWarning.objects.count()
    total_posts = Listing.objects.count()
    todays_posts = Listing.objects.filter(created_at__date=today).count()
    total_chat = ChatMessage.objects.count()
    reports_count = Report.objects.filter(handled=False).count()
    unverified = User.objects.filter(email_verified=False).count()
    recent_users = User.objects.order_by("-date_joined")[:10]
    recent_active = User.objects.order_by("-last_login")[:10]

    context = {
        "total_users": total_users,
        "todays_users": todays_users,
        "online_users": online_users,
        "blocked": blocked,
        "spammed": spammed,
        "total_posts": total_posts,
        "todays_posts": todays_posts,
        "total_chat": total_chat,
        "reports_count": reports_count,
        "unverified": unverified,
        "recent_users": recent_users,
        "recent_active": recent_active,
    }
    return render(request, "adminpanel/dashboard.html", context)


@admin_required
def users_view(request):
    User = get_user_model()
    users = User.objects.annotate(listing_count=Count("listings")).order_by("-date_joined")[:200]
    return render(request, "adminpanel/users.html", {"users": users})
