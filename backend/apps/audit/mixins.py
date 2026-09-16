from .services import log_action


class AuditedModelMixin:
    """Log create/update/delete for a ModelViewSet.

    Set ``audit_prefix`` on the view, e.g. ``"department"`` -> ``department.create``.
    """

    audit_prefix: str = ""

    def _audit(self, verb, instance, metadata=None):
        log_action(
            self.request.user,
            f"{self.audit_prefix}.{verb}",
            target=instance,
            metadata=metadata,
            request=self.request,
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._audit("create", serializer.instance)

    def perform_update(self, serializer):
        changed = sorted(serializer.validated_data.keys())
        super().perform_update(serializer)
        self._audit("update", serializer.instance, {"fields": changed})

    def perform_destroy(self, instance):
        pk = instance.pk
        self._audit("delete", instance, {"repr": str(instance)})
        super().perform_destroy(instance)
        instance.pk = pk
