import uuid
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Workspace(models.Model):
    """Top-level tenant container. Every resource belongs to a workspace."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_workspaces",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.name) or "workspace"
        slug = base_slug
        counter = 1
        while Workspace.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug


class Membership(models.Model):
    """Ties a user to a workspace with a specific role."""

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        MEMBER = "MEMBER", "Member"
        VIEWER = "VIEWER", "Viewer"

    # Role hierarchy for permission checks (higher number = more access)
    ROLE_HIERARCHY = {
        Role.VIEWER: 1,
        Role.MEMBER: 2,
        Role.MANAGER: 3,
        Role.ADMIN: 4,
        Role.OWNER: 5,
    }

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("workspace", "user")]
        ordering = ["workspace", "role"]
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"

    def __str__(self):
        return f"{self.user.email} @ {self.workspace.slug} [{self.role}]"

    def has_min_role(self, role: str) -> bool:
        """Return True if this membership's role is >= the required role."""
        return self.ROLE_HIERARCHY.get(self.role, 0) >= self.ROLE_HIERARCHY.get(role, 0)


class Invitation(models.Model):
    """Pending invitation to join a workspace. Token-based, backend-only in Part 1."""

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=Membership.Role.choices,
        default=Membership.Role.MEMBER,
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"

    def __str__(self):
        return f"Invite {self.email} → {self.workspace.slug} [{self.role}]"

    @property
    def is_valid(self):
        return self.accepted_at is None and timezone.now() < self.expires_at

    @property
    def is_accepted(self):
        return self.accepted_at is not None


class WorkspaceSettings(models.Model):
    """1-to-1 settings companion for a Workspace."""

    workspace = models.OneToOneField(
        Workspace,
        on_delete=models.CASCADE,
        related_name="settings",
        primary_key=True,
    )
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Workspace Settings"
        verbose_name_plural = "Workspace Settings"

    def __str__(self):
        return f"Settings for {self.workspace.slug}"
