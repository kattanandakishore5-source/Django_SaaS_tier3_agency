from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_project_workspaces(apps, schema_editor):
    Project = apps.get_model("core", "Project")
    Workspace = apps.get_model("tenancy", "Workspace")
    for project in Project.objects.filter(workspace__isnull=True):
        workspace = Workspace.objects.filter(owner=project.user).order_by("created_at").first()
        if workspace is not None:
            project.workspace = workspace
            project.save(update_fields=["workspace"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="workspace",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects", to="tenancy.workspace"),
        ),
        migrations.RunPython(populate_project_workspaces, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="project",
            name="workspace",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="tenancy.workspace"),
        ),
    ]
