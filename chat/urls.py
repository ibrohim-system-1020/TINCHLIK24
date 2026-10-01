from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_page, name="chat"),
    path("conversations/", views.conversations_list, name="conversations"),
    path("users/", views.chat_users, name="users"),
    path("conversations/start/", views.start_conversation, name="start_conversation"),
    path("history/", views.chat_history, name="history"),
    path("upload/", views.upload_chat_media, name="upload"),
    path("send/", views.send_message, name="send_message"),
    path("delete/<int:message_id>/", views.delete_message, name="delete_message"),
] 
