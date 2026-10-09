from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

from apps.ip_control.services import validate_ip_access
from apps.time_logs.services import (
    create_time_log_entry,
    close_time_log_entry,
    get_current_time_log_state,
)
from apps.time_logs.models import TimeLog
from apps.time_logs.serializers import (
    TimeLogSerializer,
    WorkSessionCloseInputSerializer,
)


class WorkSessionStartView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/timelogs/work-session/start/
        
        Inicia una jornada laboral para el usuario autenticado.
        """
        
        # 1. Obtener IP del request
        ip_address = request.META.get('REMOTE_ADDR')
        
        # 2. Validar que IP esté autorizada
        try:
            validate_ip_access(ip_address)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 3. Obtener asistente del usuario autenticado
        try:
            assistant = request.user.assistant
        except Exception:
            return Response(
                {'error': 'No eres un asistente registrado en el sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 4. Crear TimeLog
        try:
            time_log = create_time_log_entry(assistant)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. Serializar y retornar
        serializer = TimeLogSerializer(time_log)
        return Response(
            {'ok': True, 'session': serializer.data},
            status=status.HTTP_200_OK
        )


class WorkSessionCurrentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assistant = request.user.assistant
        except Exception:
            return Response(
                {
                    'ok': True,
                    'active_session': False,
                    'server_now': timezone.now(),
                    'session': None,
                },
                status=status.HTTP_200_OK
            )

        current_state = get_current_time_log_state(assistant)

        if not current_state['active_session']:
            return Response(
                {
                    'ok': True,
                    'active_session': False,
                    'server_now': timezone.now(),
                    'session': None,
                },
                status=status.HTTP_200_OK
            )

        serializer = TimeLogSerializer(current_state['session'])
        return Response(
            {
                'ok': True,
                'active_session': True,
                'server_now': current_state['server_now'],
                'elapsed_seconds': current_state['elapsed_seconds'],
                'session': serializer.data,
            },
            status=status.HTTP_200_OK
        )


class WorkSessionCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            assistant = request.user.assistant
        except Exception:
            return Response(
                {'error': 'No eres un asistente registrado en el sistema.'},
                status=status.HTTP_403_FORBIDDEN
            )

        payload_serializer = WorkSessionCloseInputSerializer(data=request.data)
        payload_serializer.is_valid(raise_exception=True)

        try:
            time_log = close_time_log_entry(
                assistant,
                payload=payload_serializer.validated_data,
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TimeLogSerializer(time_log)
        return Response(
            {
                'ok': True,
                'closed_session': serializer.data,
                'server_now': timezone.now(),
            },
            status=status.HTTP_200_OK
        )


class WorkSessionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assistant = request.user.assistant
        except Exception:
            return Response(
                {'ok': True, 'total_seconds': 0, 'sessions': []},
                status=status.HTTP_200_OK,
            )

        period = request.query_params.get('period', 'month')
        today = timezone.localdate()

        if period == 'day':
            period_start = today
            period_end = today + timedelta(days=1)
        elif period == 'week':
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=7)
        elif period == 'month':
            period_start = today.replace(day=1)
            next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = next_month
        else:
            return Response(
                {'detail': 'El periodo debe ser day, week o month.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period_start_datetime = timezone.make_aware(datetime.combine(period_start, datetime.min.time()))
        period_end_datetime = timezone.make_aware(datetime.combine(period_end, datetime.min.time()))
        sessions = TimeLog.objects.filter(
            assistant=assistant,
            check_out__isnull=False,
            check_in__gte=period_start_datetime,
            check_in__lt=period_end_datetime,
        ).order_by('-check_in')
        serializer = TimeLogSerializer(sessions, many=True)
        total_seconds = sum(
            max(
                0,
                item['elapsed_seconds'] - (item['break_minutes'] * 60),
            )
            for item in serializer.data
        )

        return Response(
            {
                'ok': True,
                'period': period,
                'period_start': period_start,
                'period_end': period_end,
                'total_seconds': total_seconds,
                'sessions': serializer.data,
            },
            status=status.HTTP_200_OK,
        )