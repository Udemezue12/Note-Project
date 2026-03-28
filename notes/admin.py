from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import BlockedIP, Note, SyncQueue, Tag, HistoricalRecords

User = get_user_model()
admin.site.register(User)
admin.site.register(Tag)
admin.site.register(SyncQueue)
admin.site.register(Note)


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = (
        "ip_address",
        "reason",
        "attempts",
        "is_active",
        "created_at",
        "last_attempt",
    )

    list_filter = ("is_active", "created_at")
    search_fields = ("ip_address", "reason", "user_agent")
    readonly_fields = ("created_at", "last_attempt")

    actions = ["unblock_ips"]

    @admin.action(description="Unblock selected IPs")
    def unblock_ips(self, request, queryset):
        queryset.update(is_active=False)
