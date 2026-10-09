from django.urls import path
from apps.time_logs.views import (
    WorkSessionStartView,
    WorkSessionCurrentView,
    WorkSessionCloseView,
    WorkSessionHistoryView,
    WorkSessionReportsView,
)

urlpatterns = [
    path('work-session/start/', WorkSessionStartView.as_view(), name='work-session-start'),
    path('work-session/current/', WorkSessionCurrentView.as_view(), name='work-session-current'),
    path('work-session/close/', WorkSessionCloseView.as_view(), name='work-session-close'),
    path('work-session/history/', WorkSessionHistoryView.as_view(), name='work-session-history'),
    path('reports/', WorkSessionReportsView.as_view(), name='work-session-reports'),
]