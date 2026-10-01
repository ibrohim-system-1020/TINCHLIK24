from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    participant_one = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_as_one",
    )
    participant_two = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_as_two",
    )
    participant_one_read_at = models.DateTimeField(null=True, blank=True)
    participant_two_read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["participant_one", "participant_two"],
                name="unique_direct_conversation_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(participant_one=models.F("participant_two")),
                name="direct_conversation_distinct_users",
            ),
        ]

    @classmethod
    def get_or_create_direct(cls, user_a, user_b):
        first, second = sorted((user_a, user_b), key=lambda user: user.pk)
        return cls.objects.get_or_create(participant_one=first, participant_two=second)

    def includes(self, user):
        return user.is_authenticated and user.pk in (self.participant_one_id, self.participant_two_id)

    def other_participant(self, user):
        if user.pk == self.participant_one_id:
            return self.participant_two
        if user.pk == self.participant_two_id:
            return self.participant_one
        return None

    def read_at_for(self, user):
        if user.pk == self.participant_one_id:
            return self.participant_one_read_at
        if user.pk == self.participant_two_id:
            return self.participant_two_read_at
        return None

    def __str__(self):
        return f"Conversation {self.pk}: {self.participant_one_id} - {self.participant_two_id}"


class ChatMessage(models.Model):
    MESSAGE_TYPE_TEXT = "text"
    MESSAGE_TYPE_IMAGE = "image"
    MESSAGE_TYPE_AUDIO = "audio"
    MESSAGE_TYPE_CHOICES = [
        (MESSAGE_TYPE_TEXT, "Text"),
        (MESSAGE_TYPE_IMAGE, "Image"),
        (MESSAGE_TYPE_AUDIO, "Audio"),
    ]
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_READ = "read"
    STATUS_CHOICES = [
        (STATUS_SENT, "Sent"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_READ, "Read"),
    ]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
    )
    client_id = models.UUIDField(null=True, blank=True, unique=True)
    text = models.TextField(blank=True, default="")
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default=MESSAGE_TYPE_TEXT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SENT)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    image = models.ImageField(upload_to="chat/images/", blank=True, null=True)
    audio = models.FileField(upload_to="chat/audio/", blank=True, null=True)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender} - {self.message_type} - {self.created_at}"


class ChatPresence(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_presence")
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.user} - active={self.is_active}"
