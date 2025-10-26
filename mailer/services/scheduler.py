from __future__ import annotations

import os
import threading
import time
from contextlib import suppress

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from ..models import Schedule
from .sender import dispatch_schedule

_scheduler_thread: threading.Thread | None = None
_scheduler_lock = threading.Lock()


def start_scheduler() -> None:
    global _scheduler_thread
    if os.environ.get("RUN_MAIN") == "true":  # ignore autoreload forks
        return
    with _scheduler_lock:
        if _scheduler_thread and _scheduler_thread.is_alive():
            return
        _scheduler_thread = threading.Thread(target=_worker, name="mailer-scheduler", daemon=True)
        _scheduler_thread.start()


def _worker() -> None:
    while True:
        with suppress(Exception):
            tick()
        time.sleep(settings.CRON_TICK_SECONDS)


def tick() -> None:
    now = timezone.now()
    close_old_connections()
    for schedule in Schedule.objects.select_related("message").all():
        if schedule.due(now):
            dispatch_schedule(schedule, user=None)
