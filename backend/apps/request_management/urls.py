from django.urls import path

from .views import admin_options_view, request_detail_view, requests_view

urlpatterns = [
    path('admins/', admin_options_view, name='request-admin-options'),
    path('', requests_view, name='requests'),
    path('<int:request_id>/', request_detail_view, name='request-detail'),
]
