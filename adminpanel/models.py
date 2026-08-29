from django.conf import settings
from django.db import models
from django.utils import timezone


class UserWarning(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="warnings")
    level = models.PositiveSmallIntegerField()  # 1,2,3
    reason = models.CharField(max_length=255, blank=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="given_warnings")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Warning {self.level} for {self.user}"


class UserBan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bans")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="given_bans")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    permanent = models.BooleanField(default=False)

    def is_active(self):
        if self.permanent:
            return True
        if self.expires_at and timezone.now() < self.expires_at:
            return True
        return False

    def __str__(self):
        return f"Ban for {self.user} ({'permanent' if self.permanent else 'temporary'})"


class UserMute(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mutes")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="given_mutes")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    permanent = models.BooleanField(default=False)

    def is_active(self):
        if self.permanent:
            return True
        if self.expires_at and timezone.now() < self.expires_at:
            return True
        return False

    def __str__(self):
        return f"Mute for {self.user} ({'permanent' if self.permanent else 'temporary'})"


class ChatSettings(models.Model):
    is_locked = models.BooleanField(default=False)
    lock_expires_at = models.DateTimeField(null=True, blank=True)


class AdminActionLog(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="admin_actions")
    action = models.CharField(max_length=255)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="admin_action_targets")
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Report(models.Model):
    REPORT_TARGET_USER = "user"
    REPORT_TARGET_POST = "post"
    REPORT_TARGET_CHAT = "chat"
    TARGET_CHOICES = [
        (REPORT_TARGET_USER, "user"),
        (REPORT_TARGET_POST, "post"),
        (REPORT_TARGET_CHAT, "chat"),
    ]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports_made")
    target_type = models.CharField(max_length=10, choices=TARGET_CHOICES)
    target_id = models.CharField(max_length=255)
    reason = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    handled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="handled_reports")

    class Meta:
        ordering = ["-created_at"]


class Announcement(models.Model):
    LEVEL_INFO = "info"
    LEVEL_WARNING = "warning"
    LEVEL_IMPORTANT = "important"
    LEVEL_MAINTENANCE = "maintenance"
    LEVEL_CHOICES = [
        (LEVEL_INFO, "Info"),
        (LEVEL_WARNING, "Warning"),
        (LEVEL_IMPORTANT, "Important"),
        (LEVEL_MAINTENANCE, "Maintenance"),
    ]

    admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="announcements")
    level = models.CharField(max_length=32, choices=LEVEL_CHOICES, default=LEVEL_INFO)
    title = models.CharField(max_length=255)
    text = models.TextField()
    target_all = models.BooleanField(default=True)
    target_online_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class SiteSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)
    maintenance_title = models.CharField(max_length=255, blank=True)
    maintenance_text = models.TextField(blank=True)
    maintenance_expires_at = models.DateTimeField(null=True, blank=True)
