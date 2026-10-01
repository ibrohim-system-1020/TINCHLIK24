try:
    from asgiref.sync import async_to_sync
except Exception:
    def async_to_sync(func):
        return func

try:
    from channels.layers import get_channel_layer
except Exception:
    def get_channel_layer():
        return None
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.html import escape

from .models import ChatMessage, ChatPresence, Conversation


User = get_user_model()


def _direct_chat_user_group(user_id):
    return f"direct_chat_user_{user_id}"


def _can_delete_message(user, message):
    if not user or not user.is_authenticated or message.sender_id != user.id or message.is_deleted:
        return False
    return timezone.now() <= message.created_at + timedelta(minutes=15)


def _serialize_chat_message(message, user=None):
    is_mine = bool(user and message.sender_id == user.id)
    payload = {
        "id": message.id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.get_full_name() or message.sender.email,
        "sender_email": message.sender.email,
        "sender_avatar": message.sender.profile_photo_url,
        "text": message.text,
        "message_type": message.message_type,
        "created_at": message.created_at.isoformat(),
        "conversation_id": message.conversation_id,
        "status": message.status,
        "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "reply_to": None,
        "image_url": message.image.url if message.image else None,
        "audio_url": message.audio.url if message.audio else None,
        "conversation_id": message.conversation_id,
        "status": message.status,
        "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "is_mine": is_mine,
        "can_delete": _can_delete_message(user, message),
    }
    if message.reply_to_id:
        payload["reply_to"] = {
            "id": message.reply_to_id,
            "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
            "text": message.reply_to.text or "",
        }
    return payload


def _broadcast_chat_message(message, user=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

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
        "can_delete": _can_delete_message(user, message),
    }

    if message.reply_to_id:
        payload["reply_to"] = {
            "id": message.reply_to_id,
            "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
            "text": escape(message.reply_to.text or ""),
        }

    if message.conversation_id:
        event = {"type": "new_message", "conversation_id": message.conversation_id, "message": payload}
        for participant_id in (message.conversation.participant_one_id, message.conversation.participant_two_id):
            async_to_sync(channel_layer.group_send)(
                _direct_chat_user_group(participant_id),
                {"type": "direct_event", "event": event},
            )
        return

    async_to_sync(channel_layer.group_send)("global_chat", {"type": "chat_message_event", "message": payload})


def _broadcast_delete_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    if message.conversation_id:
        event = {"type": "delete_message", "conversation_id": message.conversation_id, "message_id": message.pk}
        for participant_id in (message.conversation.participant_one_id, message.conversation.participant_two_id):
            async_to_sync(channel_layer.group_send)(
                _direct_chat_user_group(participant_id),
                {"type": "direct_event", "event": event},
            )
        return
    async_to_sync(channel_layer.group_send)(
        "global_chat",
        {
            "type": "delete_message_event",
            "message_id": message.pk,
        },
    )


@login_required
def chat_page(request):
    return render(request, "chat/chat.html", {"start_user_id": request.GET.get("user", "")})


@login_required
def conversations_list(request):
    latest_message = ChatMessage.objects.filter(
        conversation_id=OuterRef("pk"), is_deleted=False
    ).order_by("-created_at", "-pk")
    unread_messages = (
        ChatMessage.objects.filter(
            conversation_id=OuterRef("pk"), is_deleted=False, read_at__isnull=True
        )
        .exclude(sender_id=request.user.pk)
        .order_by()
        .values("conversation_id")
        .annotate(total=Count("pk"))
        .values("total")
    )
    conversations = list(
        Conversation.objects.filter(
            Q(participant_one=request.user) | Q(participant_two=request.user)
        )
        .select_related("participant_one", "participant_two")
        .annotate(
            preview_text=Subquery(latest_message.values("text")[:1]),
            preview_type=Subquery(latest_message.values("message_type")[:1]),
            preview_at=Subquery(latest_message.values("created_at")[:1]),
            unread_count=Coalesce(Subquery(unread_messages, output_field=IntegerField()), Value(0)),
        )
        .order_by("-updated_at", "-pk")[:100]
    )
    other_ids = [conversation.other_participant(request.user).pk for conversation in conversations]
    online_ids = set(ChatPresence.objects.filter(
        user_id__in=other_ids,
        is_active=True,
        last_seen__gte=timezone.now() - timedelta(minutes=5),
    ).values_list("user_id", flat=True))

    results = []
    for conversation in conversations:
        other = conversation.other_participant(request.user)
        preview = conversation.preview_text or ""
        if conversation.preview_type == ChatMessage.MESSAGE_TYPE_IMAGE:
            preview = "Rasm yuborildi"
        elif conversation.preview_type == ChatMessage.MESSAGE_TYPE_AUDIO:
            preview = "Ovozli xabar yuborildi"
        results.append({
            "id": conversation.pk,
            "participant": {
                "id": other.pk,
                "name": other.get_full_name() or "Foydalanuvchi",
                "avatar": other.profile_photo_url,
                "is_online": other.pk in online_ids,
            },
            "last_message": preview,
            "last_message_at": conversation.preview_at.isoformat() if conversation.preview_at else None,
            "unread_count": conversation.unread_count,
        })
    return JsonResponse({"conversations": results})


@login_required
def chat_users(request):
    query = (request.GET.get("q") or "").strip()
    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if query:
        users = users.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
        )
    users = users.only("id", "first_name", "last_name", "last_seen", "telegram_photo_url").order_by("first_name", "last_name")[:30]
    online_threshold = timezone.now() - timedelta(minutes=5)
    return JsonResponse({"users": [{
        "id": user.pk,
        "name": user.get_full_name() or "Foydalanuvchi",
        "avatar": user.profile_photo_url,
        "is_online": bool(user.last_seen and user.last_seen >= online_threshold),
    } for user in users]})


@login_required
def start_conversation(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    try:
        payload = json.loads(request.body or b"{}")
        other_user_id = int(payload.get("user_id"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Foydalanuvchi tanlanmadi."}, status=400)
    if other_user_id == request.user.pk:
        return JsonResponse({"error": "O‘zingiz bilan suhbat ochib bo‘lmaydi."}, status=400)
    other_user = get_object_or_404(User, pk=other_user_id, is_active=True)
    try:
        with transaction.atomic():
            conversation, _ = Conversation.get_or_create_direct(request.user, other_user)
    except IntegrityError:
        conversation = Conversation.objects.get(
            participant_one_id=min(request.user.pk, other_user.pk),
            participant_two_id=max(request.user.pk, other_user.pk),
        )
    return JsonResponse({"ok": True, "conversation_id": conversation.pk})


@login_required
def chat_history(request):
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    per_page = 30
    conversation = None
    conversation_id = request.GET.get("conversation")
    if conversation_id:
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except (Conversation.DoesNotExist, ValueError):
            return JsonResponse({"error": "Conversation not found."}, status=404)
        if not conversation.includes(request.user):
            return JsonResponse({"error": "Permission denied."}, status=403)
        queryset = ChatMessage.objects.filter(conversation=conversation, is_deleted=False)
    else:
        queryset = ChatMessage.objects.filter(conversation__isnull=True, is_deleted=False)
    queryset = queryset.select_related("sender", "reply_to", "reply_to__sender").order_by("-created_at", "-pk")
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    messages = list(reversed(page_obj.object_list))
    return JsonResponse({
        "current_user_id": request.user.id,
        "conversation_id": conversation.pk if conversation else None,
        "messages": [
            {
                "id": message.id,
                "sender_id": message.sender_id,
                "sender_name": message.sender.get_full_name() or message.sender.email,
                "sender_email": message.sender.email,
                "sender_avatar": message.sender.profile_photo_url,
                "text": message.text,
                "message_type": message.message_type,
                "created_at": message.created_at.isoformat(),
                "conversation_id": message.conversation_id,
                "status": message.status,
                "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
                "read_at": message.read_at.isoformat() if message.read_at else None,
                "reply_to": None if not message.reply_to else {
                    "id": message.reply_to_id,
                    "sender_name": message.reply_to.sender.get_full_name() or message.reply_to.sender.email,
                    "text": message.reply_to.text or "",
                },
                "image_url": message.image.url if message.image else None,
                "audio_url": message.audio.url if message.audio else None,
                "is_mine": message.sender_id == request.user.id,
                "can_delete": _can_delete_message(request.user, message),
            }
            for message in messages
        ],
        "page": page_obj.number,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "total_pages": paginator.num_pages,
    })


@login_required
def send_message(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    else:
        payload = request.POST

    text = (payload.get("message") if isinstance(payload, dict) else payload.get("message", "")) or ""
    text = str(text).strip()

    if not text:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)

    if len(text) > 4000:
        return JsonResponse({"error": "Message is too long."}, status=400)

    message = ChatMessage.objects.create(
        sender=request.user,
        text=text,
        message_type=ChatMessage.MESSAGE_TYPE_TEXT,
    )
    _broadcast_chat_message(message, request.user)
    return JsonResponse({
        "ok": True,
        "message": _serialize_chat_message(message, request.user),
    })


@login_required
def delete_message(request, message_id):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        message = ChatMessage.objects.get(id=message_id, sender=request.user, is_deleted=False)
    except ChatMessage.DoesNotExist:
        return JsonResponse({"error": "Message not found or permission denied."}, status=403)

    if timezone.now() > message.created_at + timedelta(minutes=15):
        return JsonResponse({"error": "Delete window expired."}, status=403)

    message.is_deleted = True
    message.text = "[Deleted by user]"
    message.save(update_fields=["is_deleted", "text", "updated_at"])
    _broadcast_delete_message(message)
    return JsonResponse({"ok": True, "message_id": message.id})


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
    conversation = None
    conversation_id = request.POST.get("conversation_id")
    if conversation_id:
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except (Conversation.DoesNotExist, ValueError):
            return JsonResponse({"error": "Conversation not found."}, status=404)
        if not conversation.includes(request.user):
            return JsonResponse({"error": "Permission denied."}, status=403)

    message = ChatMessage.objects.create(
        sender=request.user,
        text=text,
        message_type=message_type,
        conversation=conversation,
        image=request.FILES.get("image"),
        audio=request.FILES.get("audio"),
    )
    if conversation:
        conversation.updated_at = message.created_at
        conversation.save(update_fields=["updated_at"])
    if conversation:
        conversation.updated_at = message.created_at
        conversation.save(update_fields=["updated_at"])
    _broadcast_chat_message(message, request.user)
    return JsonResponse({
        "id": message.id,
        "type": message_type,
        "url": message.image.url if message.image else message.audio.url,
        "message": _serialize_chat_message(message, request.user),
    })
