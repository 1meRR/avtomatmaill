from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

try:  # pragma: no cover - optional dependency check
    from telegram import Bot
except ImportError:  # pragma: no cover - allow offline dev
    Bot = None

from ..models import DeliveryLog, Message, Schedule


@dataclass
class DispatchResult:
    schedule_id: int
    channel: str
    status: str
    detail: str = ""
    dry_run: bool = False


def dispatch_schedule(schedule: Schedule, user, manual: bool = False) -> DispatchResult:
    if schedule.is_paused or not schedule.message.is_active:
        return DispatchResult(schedule.id, "system", "skipped", "Schedule is paused", dry_run=False)

    message = schedule.message
    now = timezone.now()
    results: list[DispatchResult] = []
    for channel in message.targets():
        if channel == "email":
            results.append(_send_email(schedule, message))
        elif channel == "telegram":
            results.append(_send_telegram(schedule, message))
    schedule.last_run_at = now
    schedule.save(update_fields=["last_run_at"])
    for result in results:
        DeliveryLog.objects.create(
            schedule=schedule,
            channel=result.channel,
            status=result.status,
            detail=result.detail,
        )
    return results[-1] if results else DispatchResult(schedule.id, "system", "skipped", "No channels")


def _send_email(schedule: Schedule, message: Message) -> DispatchResult:
    if not message.email_to:
        return DispatchResult(schedule.id, "email", "skipped", "No email target", dry_run=False)
    try:
        send_mail(
            message.subject or message.name,
            message.body,
            settings.DEFAULT_FROM_EMAIL,
            [message.email_to],
            fail_silently=False,
        )
    except Exception as exc:  # pragma: no cover - depends on SMTP
        return DispatchResult(schedule.id, "email", "error", str(exc))
    return DispatchResult(schedule.id, "email", "sent")


def _send_telegram(schedule: Schedule, message: Message) -> DispatchResult:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = message.telegram_chat_id or settings.TELEGRAM_DEFAULT_CHAT_ID
    if not (token and chat_id):
        return DispatchResult(schedule.id, "telegram", "skipped", "No telegram target")
    if Bot is None:
        return DispatchResult(schedule.id, "telegram", "error", "python-telegram-bot not installed")
    try:
        Bot(token=token).send_message(chat_id=chat_id, text=message.telegram_text or message.body)
    except Exception as exc:  # pragma: no cover - depends on network
        return DispatchResult(schedule.id, "telegram", "error", str(exc))
    return DispatchResult(schedule.id, "telegram", "sent")
