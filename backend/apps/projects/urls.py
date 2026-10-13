from django.urls import path

from apps.projects.views import (
    ActiveProjectListView,
    ActiveCoordinatorListView,
    AdminProjectListView,
    AdminProjectDetailView,
)


urlpatterns = [
    path('active/', ActiveProjectListView.as_view(), name='projects-active-list'),
    path('admin/', AdminProjectListView.as_view(), name='projects-admin-list'),
    path('admin/<int:project_id>/', AdminProjectDetailView.as_view(), name='projects-admin-detail'),
    path('coordinators/active/', ActiveCoordinatorListView.as_view(), name='coordinators-active-list'),
]