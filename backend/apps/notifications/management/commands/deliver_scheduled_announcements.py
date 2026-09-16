from django.core.management.base import BaseCommand

from apps.notifications.announcements import deliver_due


class Command(BaseCommand):
    help = "Notify recipients of scheduled announcements that have gone live. Run every minute."

    def handle(self, *args, **options):
        count = deliver_due()
        self.stdout.write(self.style.SUCCESS(f"deliver_scheduled_announcements: delivered {count}"))
