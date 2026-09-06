from django.db import models
from apps.accounts.models import CustomUser
from apps.tenancy.models import Workspace
from apps.tenancy.querysets import WorkspaceScopedManager


class Project(models.Model):
    objects = WorkspaceScopedManager()

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='projects')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
