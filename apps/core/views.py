from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.billing.entitlements import get_user_limit, LIMIT_PROJECTS
from apps.tenancy.services import get_or_create_default_workspace_for_user
from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            workspace = get_or_create_default_workspace_for_user(self.request.user)
        self.request.workspace = workspace
        return Project.objects.for_workspace(workspace)

    def perform_create(self, serializer):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            workspace = get_or_create_default_workspace_for_user(self.request.user)
        self.request.workspace = workspace

        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(id=self.request.user.id)
            project_count = Project.objects.filter(workspace=workspace, user=user).count()
            limit = get_user_limit(user, LIMIT_PROJECTS)

            if project_count >= limit:
                raise ValidationError({"detail": f"You have reached your limit of {limit} projects. Please upgrade your plan."})

            serializer.save(user=user, workspace=workspace)
