from django.contrib.auth import get_user_model
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth import logout


class LastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            User = get_user_model()

            # update last seen timestamp
            User.objects.filter(pk=request.user.pk).update(last_seen=timezone.now())

            # Lazy import adminpanel models to avoid AppRegistryNotReady on import
            try:
                from adminpanel.models import UserBan, UserMute

                # Auto-expire temporary bans and mutes whose time has passed
                now = timezone.now()
                try:
                    UserBan.objects.filter(permanent=False, expires_at__lte=now).delete()
                    UserMute.objects.filter(permanent=False, expires_at__lte=now).delete()
                except Exception:
                    pass

                # If user has an active ban and is not admin, log them out and show block page
                try:
                    active_ban = UserBan.objects.filter(user=request.user).first()
                    if active_ban and active_ban.is_active() and not (
                        request.user.is_staff and request.user.is_superuser
                    ):
                        logout(request)
                        return render(request, "accounts/blocked.html", {"ban": active_ban})
                except Exception:
                    pass
            except Exception:
                # adminpanel may not be ready yet; ignore
                pass

        response = self.get_response(request)

        return response