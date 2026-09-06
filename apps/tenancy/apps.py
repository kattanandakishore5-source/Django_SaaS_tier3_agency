from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenancy"
    verbose_name = "Tenancy"

    def ready(self):
        # Import signal handlers so they are registered on app startup.
        import apps.tenancy.signals  # noqa: F401
