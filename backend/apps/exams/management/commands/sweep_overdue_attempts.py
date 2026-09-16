from django.core.management.base import BaseCommand

from apps.exams.attempts import sweep_overdue


class Command(BaseCommand):
    help = "Submit exam attempts whose deadline has passed. Run every minute from cron."

    def handle(self, *args, **options):
        count = sweep_overdue()
        self.stdout.write(self.style.SUCCESS(f"sweep_overdue_attempts: {count} attempts submitted"))
