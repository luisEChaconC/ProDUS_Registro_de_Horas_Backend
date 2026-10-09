from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db import models

from core.permissions import IsAdminOrCoordinator

from .serializers import ScheduleCreateSerializer, ScheduleDetailSerializer
from .models import Schedule


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_schedule_view(request):
    try:
        assistant = request.user.assistant
    except Exception:
        return Response({'ok': True, 'schedule': None}, status=status.HTTP_200_OK)

    schedule = Schedule.objects.filter(
        assistant=assistant,
        valid_from__lte=timezone.localdate(),
    ).filter(
        models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=timezone.localdate())
    ).prefetch_related('blocks').order_by('-valid_from').first()

    return Response({
        'ok': True,
        'schedule': ScheduleDetailSerializer(schedule).data if schedule else None,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrCoordinator])
def create_assistant_schedule_view(request):
    serializer = ScheduleCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    schedule = serializer.save()

    return Response(
        {
            'ok': True,
            'schedule': ScheduleDetailSerializer(schedule).data,
        },
        status=status.HTTP_201_CREATED)
