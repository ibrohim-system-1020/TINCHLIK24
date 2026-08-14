import logging
from datetime import datetime, timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import AdminAuditLog, LoginHistory, User


@sync_to_async
def get_recent_audit_logs(limit: int = 10):
    return list(AdminAuditLog.objects.order_by("-created_at")[:limit])

logger = logging.getLogger(__name__)


@sync_to_async
def get_admin_whitelist():
    return getattr(settings, "ADMIN_TELEGRAM_IDS", [])


@sync_to_async
def get_dashboard_stats():
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = User.objects.count()
    today_users = User.objects.filter(date_joined__gte=today).count()
    week_users = User.objects.filter(date_joined__gte=week_ago).count()
    month_users = User.objects.filter(date_joined__gte=month_ago).count()
    online_users = User.objects.filter(last_seen__gte=now - timedelta(minutes=getattr(settings, "ONLINE_THRESHOLD_MINUTES", 5))).count()
    verified_users = User.objects.filter(is_phone_verified=True).count()
    telegram_users = User.objects.filter(telegram_id__isnull=False).count()
    total_logins = LoginHistory.objects.count()

    return {
        "total_users": total_users,
        "today_users": today_users,
        "week_users": week_users,
        "month_users": month_users,
        "online_users": online_users,
        "verified_users": verified_users,
        "telegram_users": telegram_users,
        "total_logins": total_logins,
    }


@sync_to_async
def get_user_list(page: int = 1, page_size: int = 8, filter_q: Optional[Q] = None):
    queryset = User.objects.all().order_by("-date_joined")

    if filter_q is not None:
        queryset = queryset.filter(filter_q)

    offset = (page - 1) * page_size
    users = list(queryset[offset:offset + page_size])
    total = queryset.count()

    return users, total


@sync_to_async
def get_user_by_id(user_id: int):
    return User.objects.filter(id=user_id).first()


@sync_to_async
def get_user_by_search(term: str):
    term = term.strip()
    return User.objects.filter(
        Q(first_name__icontains=term)
        | Q(last_name__icontains=term)
        | Q(email__icontains=term)
        | Q(telefon__icontains=term)
        | Q(telegram_username__icontains=term)
        | Q(telegram_id__icontains=term)
        | Q(id__iexact=term)
    ).order_by("-date_joined").first()


@sync_to_async
def get_user_login_count(user):
    return LoginHistory.objects.filter(user=user).count()


@sync_to_async
def get_weekly_top_users(limit: int = 5):
    week_ago = timezone.now() - timedelta(days=7)
    return list(
        User.objects.annotate(
            week_logins=Count("login_history", filter=Q(login_history__logged_in_at__gte=week_ago))
        )
        .filter(week_logins__gt=0)
        .order_by("-week_logins")[:limit]
    )


@sync_to_async
def get_all_time_top_users(limit: int = 5):
    return list(
        User.objects.annotate(total_logins=Count("login_history"))
        .filter(total_logins__gt=0)
        .order_by("-total_logins")[:limit]
    )


@sync_to_async
def get_user_login_history(user, limit: int = 10):
    return list(LoginHistory.objects.filter(user=user).order_by("-logged_in_at")[:limit])


@sync_to_async
def create_audit_log(admin_telegram_id: int, admin_username: str, action: str, target_user=None, details: str = ""):
    AdminAuditLog.objects.create(
        admin_telegram_id=admin_telegram_id,
        admin_username=admin_username,
        action=action,
        target_user=target_user,
        details=details,
    )
