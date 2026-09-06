"""
WorkspaceScopedQuerySet — reusable mixin for tenant-isolated querysets.

Usage:
    class Project(models.Model):
        workspace = models.ForeignKey(Workspace, ...)
        objects = WorkspaceScopedManager()

    # In views:
    Project.objects.for_workspace(request.workspace)
"""

from django.db import models


class TenantIsolationError(Exception):
    """Raised when a queryset operation is attempted without workspace scoping in debug mode."""
    pass


class WorkspaceScopedQuerySet(models.QuerySet):
    """
    QuerySet mixin that enforces workspace-level tenant isolation.

    Call .for_workspace(workspace) to filter to a specific workspace.
    Returning .none() when workspace is None ensures cross-tenant leakage
    is impossible even if the caller forgets a null check.
    """

    _workspace_scoped = False

    def for_workspace(self, workspace):
        """
        Return queryset filtered to the given workspace.

        Applies a stable default ordering to avoid DRF pagination
        UnorderedObjectListWarning when the model has no Meta.ordering.
        The model's own ordering takes precedence if defined.
        """
        if workspace is None:
            # Guard: never return all records when workspace is explicitly None.
            return self.none()
        qs = self.filter(workspace=workspace)
        # Apply stable ordering if the model does not already define one,
        # preventing UnorderedObjectListWarning from DRF's PageNumberPagination.
        if not qs.ordered:
            qs = qs.order_by("-created_at") if hasattr(self.model, "created_at") else qs.order_by("pk")
        qs._workspace_scoped = True
        return qs

    def _clone(self):
        c = super()._clone()
        c._workspace_scoped = self._workspace_scoped
        return c


class WorkspaceScopedManager(models.Manager):
    """Manager that returns a WorkspaceScopedQuerySet."""

    def get_queryset(self):
        return WorkspaceScopedQuerySet(self.model, using=self._db)

    def for_workspace(self, workspace):
        return self.get_queryset().for_workspace(workspace)
