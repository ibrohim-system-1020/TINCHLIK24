from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("register/telegram/<uuid:token>/", views.register_telegram_link_view, name="register_telegram_link"),
    path("register/telegram/", views.register_telegram_wait, name="register_telegram_wait"),
    path("register/status/<uuid:token>/", views.pending_status_api, name="pending_status_api"),
    path("register/verify/<uuid:token>/", views.verify_code_view, name="verify_code"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/security/", views.security_view, name="security"),
]

