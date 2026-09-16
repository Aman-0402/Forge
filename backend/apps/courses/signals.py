from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import StudentProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def auto_enroll_on_user_save(sender, instance, raw=False, **kwargs):
    if raw or instance.role != "student":
        return
    from .enrollment import sync_student_auto_enrollments

    sync_student_auto_enrollments(instance)


@receiver(post_save, sender=StudentProfile)
def auto_enroll_on_profile_save(sender, instance, raw=False, **kwargs):
    if raw or not instance.batch:
        return
    from .enrollment import sync_student_auto_enrollments

    sync_student_auto_enrollments(instance.user)
