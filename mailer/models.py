from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from croniter import croniter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

User = get_user_model()


class Message(models.Model):
    name = models.CharField(max_length=120)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text="Текст письма для Email")
    telegram_text = models.TextField(help_text="Текст для Telegram", blank=True)
    email_to = models.EmailField(blank=True)
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="messages",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - human readable
        return self.name

    def targets(self) -> Iterable[str]:
        if self.email_to:
            yield "email"
        if self.telegram_chat_id or settings.TELEGRAM_DEFAULT_CHAT_ID:
            yield "telegram"


class Schedule(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="schedules")
    cron = models.CharField(max_length=120, help_text="Cron-выражение, например '*/5 * * * *'")
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)
    interval_seconds = models.PositiveIntegerField(
        default=settings.MESSAGE_DEFAULT_INTERVAL,
        validators=[MinValueValidator(10)],
        help_text="Минимальный интервал между отправками",
    )
    max_per_minute = models.PositiveIntegerField(
        default=settings.MESSAGE_MAX_PER_MINUTE,
        validators=[MinValueValidator(1)],
        help_text="Ограничение по количеству отправок в минуту",
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - admin friendly
        return f"{self.message.name} @ {self.cron}"

    def due(self, now=None) -> bool:
        now = now or timezone.now()
        if self.is_paused or not self.message.is_active:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        if self.last_run_at and (now - self.last_run_at).total_seconds() < self.interval_seconds:
            return False
        naive_now = now.replace(tzinfo=None)
        if not croniter.match(self.cron, naive_now):
            return False
        return self.respect_rate_limit(now)

    def respect_rate_limit(self, now):
        window_start = now - timedelta(minutes=1)
        return (
            self.logs.filter(created_at__gte=window_start).count() < self.max_per_minute
        )

    def next_run(self, now=None):
        base = (now or timezone.now()).replace(tzinfo=None)
        next_dt = croniter(self.cron, base).get_next(datetime)
        return timezone.make_aware(next_dt, timezone.get_current_timezone())


class DeliveryLog(models.Model):
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("telegram", "Telegram"),
    ]

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=40)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.schedule_id}:{self.channel}:{self.status}"
