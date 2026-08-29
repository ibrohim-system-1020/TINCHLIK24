from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("users/", views.users_view, name="users"),
]
