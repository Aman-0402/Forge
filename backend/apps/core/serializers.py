from rest_framework import serializers

from .models import MarketingStat, SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["registration_open", "maintenance_mode", "maintenance_message"]


class MarketingStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingStat
        fields = ["id", "order", "value", "suffix", "description"]
