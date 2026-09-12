import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_workspaces(apps, schema_editor):
    Workspace = apps.get_model("tenancy", "Workspace")
    Membership = apps.get_model("tenancy", "Membership")
    WorkspaceSettings = apps.get_model("tenancy", "WorkspaceSettings")
    User = apps.get_model(settings.AUTH_USER_MODEL)

    for user in User.objects.all():
        workspace = Workspace.objects.filter(owner=user).order_by("created_at").first()
        if workspace is None:
            workspace_name = f"{user.first_name or user.email.split('@')[0].title()} Workspace"
            workspace = Workspace.objects.create(
                id=uuid.uuid4(),
                name=workspace_name,
                slug=f"user-{user.id}-workspace",
                owner=user,
                is_active=True,
            )
        Membership.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={"role": "OWNER", "is_active": True},
        )
        WorkspaceSettings.objects.get_or_create(
            workspace=workspace,
            defaults={"timezone": "UTC", "locale": "en"},
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="owned_workspaces", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name": "Workspace",
                "verbose_name_plural": "Workspaces",
            },
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MANAGER", "Manager"), ("MEMBER", "Member"), ("VIEWER", "Viewer")], default="MEMBER", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.DB_CASCADE, related_name="workspace_memberships", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.DB_CASCADE, related_name="memberships", to="tenancy.workspace")),
            ],
            options={
                "ordering": ["workspace", "role"],
                "verbose_name": "Membership",
                "verbose_name_plural": "Memberships",
                "unique_together": {("workspace", "user")},
            },
        ),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MANAGER", "Manager"), ("MEMBER", "Member"), ("VIEWER", "Viewer")], default="MEMBER", max_length=20)),
                ("token", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invited_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_invitations", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.DB_CASCADE, related_name="invitations", to="tenancy.workspace")),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Invitation",
                "verbose_name_plural": "Invitations",
            },
        ),
        migrations.CreateModel(
            name="WorkspaceSettings",
            fields=[
                ("workspace", models.OneToOneField(on_delete=django.db.models.deletion.DB_CASCADE, primary_key=True, related_name="settings", serialize=False, to="tenancy.workspace")),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("locale", models.CharField(default="en", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Workspace Settings",
                "verbose_name_plural": "Workspace Settings",
            },
        ),
        migrations.RunPython(create_default_workspaces, migrations.RunPython.noop),
    ]
