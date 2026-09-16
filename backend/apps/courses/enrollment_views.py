from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core.permissions import IsStudent

from . import enrollment as services
from .enrollment_serializers import EnrollmentSerializer
from .models import Enrollment
from .permissions import can_manage_course


class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsStudent]
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Enrollment.objects.none()
        return Enrollment.objects.filter(student=self.request.user).select_related(
            "course__instructor", "student__student_profile"
        )


class EnrollmentViewSet(
    mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Single enrollment. Managers see and remove; students see their own."""

    serializer_class = EnrollmentSerializer
    queryset = Enrollment.objects.select_related("course__instructor", "student__student_profile")

    def get_object(self):
        enrollment = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        user = self.request.user
        is_owner = enrollment.student_id == user.pk
        if self.request.method == "DELETE":
            if not can_manage_course(user, enrollment.course):
                raise PermissionDenied(
                    "Only the course instructors or an admin can remove students."
                )
        elif not (is_owner or can_manage_course(user, enrollment.course)):
            raise PermissionDenied()
        return enrollment

    def destroy(self, request, *args, **kwargs):
        services.drop(actor=request.user, enrollment=self.get_object(), request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
