from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.html import escape

from .models import ChatMessage


def _serialize_chat_message(message):
    payload = {
        "id": message.id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.get_full_name() or message.sender.email,
        "sender_email": message.sender.email,
        "sender_avatar": message.sender.profile_photo_url,
        "text": escape(message.text),
        "message_type": message.message_type,
        "created_at": message.created_at.isoformat(),
        "reply_to": None,
        "image_url": message.image.url if message.image else None,
        "audio_url": message.audio.url if message.audio else None,
    }
    if message.reply_to_id:
        payload["reply_to"] = {
            "id": message.reply_to_id,
            "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
            "text": escape(message.reply_to.text or ""),
        }
    return payload


def _broadcast_chat_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "global_chat",
        {
            "type": "chat_message_event",
            "message": _serialize_chat_message(message),
        },
    )


@login_required
def chat_page(request):
    return render(request, "chat/chat.html")


@login_required
def chat_history(request):
    page = int(request.GET.get("page", 1))
    per_page = 30
    queryset = ChatMessage.objects.filter(is_deleted=False).select_related("sender", "reply_to", "reply_to__sender").order_by("-created_at")
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    messages = list(reversed(page_obj.object_list))
    return JsonResponse({
        "messages": [
            {
                "id": message.id,
                "sender_id": message.sender_id,
                "sender_name": message.sender.get_full_name() or message.sender.email,
                "sender_email": message.sender.email,
                "sender_avatar": message.sender.profile_photo_url,
                "text": escape(message.text),
                "message_type": message.message_type,
                "created_at": message.created_at.isoformat(),
                "reply_to": None if not message.reply_to else {
                    "id": message.reply_to_id,
                    "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
                    "text": escape(message.reply_to.text or ""),
                },
                "image_url": message.image.url if message.image else None,
                "audio_url": message.audio.url if message.audio else None,
            }
            for message in messages
        ],
        "page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "total_pages": paginator.num_pages,
    })


@login_required
def upload_chat_media(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    if "image" not in request.FILES and "audio" not in request.FILES:
        return JsonResponse({"error": "No file provided."}, status=400)

    uploaded = request.FILES.get("image") or request.FILES.get("audio")
    if uploaded.size > 10 * 1024 * 1024:
        return JsonResponse({"error": "File is too large."}, status=400)

    message_type = "image" if request.FILES.get("image") else "audio"
    text = request.POST.get("text", "")
    message = ChatMessage.objects.create(
        sender=request.user,
        text=text,
        message_type=message_type,
        image=request.FILES.get("image"),
        audio=request.FILES.get("audio"),
    )
    _broadcast_chat_message(message)
    return JsonResponse({
        "id": message.id,
        "type": message_type,
        "url": message.image.url if message.image else message.audio.url,
    })
