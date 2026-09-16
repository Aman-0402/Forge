from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

ADMIN = ("admin@forge.local", "Admin@12345")
FACULTY = [("faculty1@forge.local", "Faculty@12345"), ("faculty2@forge.local", "Faculty@12345")]
STUDENTS = [(f"student{i}@forge.local", "Student@12345") for i in range(1, 6)]


class Command(BaseCommand):
    help = "Create development users (idempotent). Never run in production."

    def handle(self, *args, **options):
        created = 0
        if not User.objects.filter(email=ADMIN[0]).exists():
            User.objects.create_superuser(email=ADMIN[0], password=ADMIN[1], first_name="Admin")
            created += 1
        for role, rows in ((User.Role.FACULTY, FACULTY), (User.Role.STUDENT, STUDENTS)):
            for email, password in rows:
                if User.objects.filter(email=email).exists():
                    continue
                User.objects.create_user(
                    email=email,
                    password=password,
                    role=role,
                    first_name=email.split("@")[0].capitalize(),
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"seed_dev: {created} users created"))
