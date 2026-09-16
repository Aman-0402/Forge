from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FacultyProfile, StudentProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_for_role(sender, instance, **kwargs):
    """Every student has a StudentProfile, every faculty a FacultyProfile.

    Old profiles are kept when a role changes so no data is lost.
    """
    if instance.role == "student":
        StudentProfile.objects.get_or_create(user=instance)
    elif instance.role == "faculty":
        FacultyProfile.objects.get_or_create(user=instance)
