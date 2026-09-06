from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    workspace = models.ForeignKey(
        'tenancy.Workspace', null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs'
    )
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=1024)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def save(self, *args, **kwargs):
        # Make immutable: prevent updates once created
        if self.pk is not None:
            raise Exception("AuditLog records are immutable and cannot be updated")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion
        raise Exception("AuditLog records are immutable and cannot be deleted")

    def __str__(self):
        ts = self.created_at.isoformat() if isinstance(self.created_at, timezone.datetime) else str(self.created_at)
        user = getattr(self.user, 'email', None) or 'anonymous'
        return f"{ts} - {self.action} - {user} - {self.path}"
