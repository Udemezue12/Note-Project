import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords
from .encryption import encrypt_text, decrypt_text


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, unique=True)

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.username)


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="tags")
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "tags"
        indexes = [
            models.Index(fields=["created_at"], name="idx_tags"),
            models.Index(fields=["user", "is_deleted"], name="idx_user_tags"),
        ]
        unique_together = ("user", "name")
        ordering = ["-created_at"]


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="notes")

    title = models.CharField(max_length=255)

    content = models.TextField()

    tag = models.ForeignKey(
        Tag,
        on_delete=models.PROTECT,
        related_name="notes"
    )

    is_pinned = models.BooleanField(default=False)

    is_archived = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    version = models.IntegerField(default=1)

    last_synced = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.content.startswith("gAAAA"):  
            self.content = encrypt_text(self.content)

        super().save(*args, **kwargs)

    def decrypted_content(self):
        return decrypt_text(self.content)

    class Meta:
        db_table = "notes"
        indexes = [
            models.Index(fields=["user", "is_deleted"]),
            models.Index(fields=["created_at"], name="idx_notes"),
        ]
        ordering = ["-created_at"]


class SyncQueue(models.Model):
    ACTIONS = (("create", "create"), ("update",
               "update"), ("delete", "delete"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    note = models.OneToOneField(Note, on_delete=models.CASCADE)

    action = models.CharField(max_length=20, choices=ACTIONS)

    synced = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["synced"]),
            models.Index(fields=["updated_at"]),
        ]


class BlacklistedToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    token = models.CharField(max_length=512, unique=True)

    blacklisted_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blacklisted_tokens"
        indexes = [
            models.Index(fields=["token"], name="idx_blacklisted_token"),
        ]

    def __str__(self):
        return str(self.token)


class BlockedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=255, blank=True, null=True)
    attempts = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_attempt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ip_address} ({self.attempts})"
