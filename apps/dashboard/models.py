from django.db import models
from apps.accounts.models import CustomUser


class Dashboard(models.Model):
    """User dashboard preferences"""
    user = models.OneToOneField(CustomUser, on_delete=models.DB_CASCADE, related_name='dashboard')
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )
    sidebar_collapsed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dashboard for {self.user.email}"
