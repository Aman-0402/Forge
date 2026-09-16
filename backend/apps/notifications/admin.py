from django.contrib import admin

from .models import Announcement, Notification


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["published_at", "title", "audience", "department", "author", "expires_at"]
    list_filter = ["audience", "department"]
    search_fields = ["title", "body"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["created_at", "recipient", "kind", "title", "is_read"]
    list_filter = ["kind", "is_read"]
    search_fields = ["title", "recipient__email"]
