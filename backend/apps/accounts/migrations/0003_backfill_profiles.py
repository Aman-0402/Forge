from django.db import migrations


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    StudentProfile = apps.get_model("accounts", "StudentProfile")
    FacultyProfile = apps.get_model("accounts", "FacultyProfile")
    for user in User.objects.filter(role="student", student_profile__isnull=True):
        StudentProfile.objects.create(user=user)
    for user in User.objects.filter(role="faculty", faculty_profile__isnull=True):
        FacultyProfile.objects.create(user=user)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_facultyprofile_studentprofile")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
