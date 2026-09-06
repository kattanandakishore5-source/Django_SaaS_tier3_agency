from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import permissions

from apps.accounts.views import root_redirect

# drf_yasg (Swagger/OpenAPI) is optional in minimal test environments; import safely
try:
    from drf_yasg import openapi
    from drf_yasg.views import get_schema_view

    schema_view = get_schema_view(
        openapi.Info(
            title='Django Starter API',
            default_version='v1',
            description='Starter dashboard API',
            contact=openapi.Contact(email='kattanandakishore5@gmail.com'),
            license=openapi.License(name='MIT License'),
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )
except Exception:
    schema_view = None

from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('', root_redirect, name='root-redirect'),
    path('health/', health_check, name='health-check'),
    path('accounts/', include('apps.accounts.browser_urls')),
    path('admin/', admin.site.urls),

    path('billing/', include('apps.billing.urls')),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.tenancy.urls')),
    path('api/projects/', include('apps.core.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('dashboard/', include('apps.dashboard.views_urls')),
]


# Only add docs routes if schema_view is available
if schema_view is not None:
    urlpatterns += [
        path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
