from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("history/", views.chat_history, name="history"),
    path("upload/", views.upload_chat_media, name="upload"),
] 
