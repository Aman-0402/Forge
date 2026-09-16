from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    """Singleton (always pk=1). Backend-controlled switches the frontend reads.

    Public GET so both the marketing site and the authenticated app can show a
    maintenance banner or a closed-registration message; only admins can PATCH.
    """

    registration_open = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MarketingStat(TimeStampedModel):
    """One editable stat on the public site's outcomes section (e.g. "95%")."""

    order = models.PositiveIntegerField(default=0)
    value = models.CharField(max_length=20, help_text="e.g. '95' or '5000'")
    suffix = models.CharField(max_length=10, blank=True, help_text="e.g. '%' or '+'")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.value}{self.suffix} {self.description}".strip()
