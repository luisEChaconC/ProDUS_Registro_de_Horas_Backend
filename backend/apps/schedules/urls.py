from django.urls import path

from .views import create_assistant_schedule_view, my_schedule_view

urlpatterns = [
    path('my/', my_schedule_view, name='my_schedule'),
    path('create/', create_assistant_schedule_view, name='create_assistant_schedule'),
]
