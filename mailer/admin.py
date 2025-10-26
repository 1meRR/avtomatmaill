from django.contrib import admin

from .models import DeliveryLog, Message, Schedule


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email_to", "telegram_chat_id", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "email_to", "telegram_chat_id")
    autocomplete_fields = ("created_by",)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("message", "cron", "is_paused", "last_run_at")
    list_filter = ("is_paused",)
    search_fields = ("cron", "message__name")


@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("schedule", "channel", "status", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("schedule__message__name", "detail")
    readonly_fields = ("created_at",)
