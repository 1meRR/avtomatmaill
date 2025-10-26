from datetime import datetime

from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DeliveryLog, Message, Schedule
from .serializers import (
    DeliveryLogSerializer,
    DispatchPreviewSerializer,
    MessageSerializer,
    ScheduleSerializer,
)
from .services.sender import DispatchResult, dispatch_schedule


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs.select_related("created_by")
        return qs.filter(created_by=self.request.user)


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related("message")
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(message__created_by=self.request.user)

    @action(detail=True, methods=["post"], serializer_class=DispatchPreviewSerializer)
    def preview(self, request, pk=None):
        schedule = self.get_object()
        serializer = self.get_serializer(data=request.data or {"schedule_id": schedule.id})
        serializer.is_valid(raise_exception=True)
        dry_run = serializer.validated_data.get("dry_run", True)
        if dry_run:
            next_run = schedule.next_run(datetime.utcnow())
            return Response({"next_run": next_run, "schedule": schedule.id})
        result = dispatch_schedule(schedule, request.user, manual=True)
        return Response(DispatchResultSerializer(result).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def pause(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_paused = True
        schedule.save(update_fields=["is_paused"])
        return Response({"status": "paused"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def resume(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_paused = False
        schedule.save(update_fields=["is_paused"])
        return Response({"status": "resumed"})


class DeliveryLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliveryLogSerializer
    queryset = DeliveryLog.objects.select_related("schedule", "schedule__message")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(schedule__message__created_by=self.request.user)


class DispatchResultSerializer(DispatchPreviewSerializer):
    status = serializers.CharField()
    channel = serializers.CharField()
    detail = serializers.CharField(allow_blank=True)

    class Meta:
        fields = ["schedule_id", "dry_run", "status", "channel", "detail"]

    def to_representation(self, instance: DispatchResult):
        return {
            "schedule_id": instance.schedule_id,
            "dry_run": instance.dry_run,
            "status": instance.status,
            "channel": instance.channel,
            "detail": instance.detail,
        }
