from django.core.management.base import BaseCommand

from ...services.scheduler import tick


class Command(BaseCommand):
    help = "Запуск разовой проверки расписаний"

    def handle(self, *args, **options):
        tick()
        self.stdout.write(self.style.SUCCESS("Tick complete"))
