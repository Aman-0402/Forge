from django.core.management.base import BaseCommand

from apps.courses.enrollment import AUTO_MODES, sync_auto_enrollments
from apps.courses.models import Course


class Command(BaseCommand):
    help = "Enroll students into published courses with automatic enrollment rules."

    def handle(self, *args, **options):
        total = 0
        courses = Course.objects.filter(
            status=Course.Status.PUBLISHED, enrollment_mode__in=AUTO_MODES
        )
        for course in courses:
            total += len(sync_auto_enrollments(course))
        self.stdout.write(self.style.SUCCESS(f"sync_auto_enrollments: {total} new enrollments"))
