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


class CountRowSerializer(serializers.Serializer):
    label = serializers.CharField()
    count = serializers.IntegerField()


class TopCourseSerializer(serializers.Serializer):
    course = serializers.CharField()
    code = serializers.CharField()
    count = serializers.IntegerField()


class ActiveInactiveSerializer(serializers.Serializer):
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()


class PassFailSerializer(serializers.Serializer):
    passed = serializers.IntegerField()
    failed = serializers.IntegerField()
    ungraded = serializers.IntegerField()


class ReportsOverviewSerializer(serializers.Serializer):
    """Read-only. Field-level shape only — see apps.core.reports.overview()."""

    generated_at = serializers.DateTimeField()
    users_by_role = CountRowSerializer(many=True)
    users_active = ActiveInactiveSerializer()
    courses_by_status = CountRowSerializer(many=True)
    enrollments_by_status = CountRowSerializer(many=True)
    top_courses_by_enrollment = TopCourseSerializer(many=True)
    exam_pass_fail = PassFailSerializer()
    coding_submissions_by_verdict = CountRowSerializer(many=True)
    problems_by_difficulty = CountRowSerializer(many=True)
    contact_messages_total = serializers.IntegerField()


class DailyActivitySerializer(serializers.Serializer):
    date = serializers.DateField()
    new_users = serializers.IntegerField()
    new_enrollments = serializers.IntegerField()
    exam_attempts = serializers.IntegerField()
    code_submissions = serializers.IntegerField()


class TimeseriesSerializer(serializers.Serializer):
    days = DailyActivitySerializer(many=True)
