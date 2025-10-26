from datetime import datetime

from rest_framework import serializers

from .models import DeliveryLog, Message, Schedule


class MessageSerializer(serializers.ModelSerializer):
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Message
        fields = [
            "id",
            "name",
            "subject",
            "body",
            "telegram_text",
            "email_to",
            "telegram_chat_id",
            "created_by",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class ScheduleSerializer(serializers.ModelSerializer):
    message = serializers.PrimaryKeyRelatedField(queryset=Message.objects.all())
    next_run = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [
            "id",
            "message",
            "cron",
            "start_at",
            "end_at",
            "interval_seconds",
            "max_per_minute",
            "last_run_at",
            "is_paused",
            "created_at",
            "next_run",
        ]
        read_only_fields = ("created_at", "next_run", "last_run_at")

    def get_next_run(self, obj: Schedule) -> datetime | None:
        try:
            return obj.next_run()
        except Exception:
            return None


class DeliveryLogSerializer(serializers.ModelSerializer):
    schedule = serializers.StringRelatedField()

    class Meta:
        model = DeliveryLog
        fields = [
            "id",
            "schedule",
            "channel",
            "status",
            "detail",
            "created_at",
        ]


class DispatchPreviewSerializer(serializers.Serializer):
    schedule_id = serializers.IntegerField()
    dry_run = serializers.BooleanField(default=True)
