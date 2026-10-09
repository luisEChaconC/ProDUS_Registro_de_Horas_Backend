"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Swagger imports
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title="ProDus Registro de Horas API",
        default_version='v1',
        description="Documentación interactiva de la API",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    Endpoint raíz de la API con información básica.
    """
    return Response({
        'message': 'ProDus Registro de Horas API',
        'version': '1.0.0',
        'endpoints': {
            'auth': {
                'login': '/api/users/auth/login/',
                'refresh': '/api/users/auth/refresh/',
                'validate_ip': '/api/users/auth/validate-institute-ip/',
            },
            'users': '/api/users/users/',
            'allowed_ip_ranges': '/api/users/allowed-ip-ranges/',
        }
    })



urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Swagger/OpenAPI
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # API Root
    path('api/', api_root, name='api-root'),

    # Apps
    path('api/', include([
        path('users/', include('apps.users.urls')),
        path('timelogs/', include('apps.time_logs.urls')),
        path('projects/', include('apps.projects.urls')),
        path('schedules/', include('apps.schedules.urls')),
    ])),
]
