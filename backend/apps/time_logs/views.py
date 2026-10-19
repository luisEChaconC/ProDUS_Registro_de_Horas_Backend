from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAdmin
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from datetime import date

from apps.ip_control.services import validate_ip_access
from apps.time_logs.services import (
    create_time_log_entry,
    close_time_log_entry,
    get_current_time_log_state,
)
from apps.time_logs.models import TimeLog
from apps.time_logs.models import TimeLogStatus
from apps.users.models import Assistant
from apps.time_logs.serializers import (
    TimeLogSerializer,
    WorkSessionCloseInputSerializer,
    AdminTimeLogSerializer,
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
                {
                    'ok': True,
                    'total_seconds': 0,
                    'sessions': [],
                    'cumulative_total_seconds': 0,
                    'expected_total_seconds': 0,
                    'deficit_seconds': 0,
                },
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
        today = timezone.localdate()
        tracked_until = min(today, assistant.end_date) if assistant.end_date else today
        reactivation_week_start = assistant.last_reactivation_date - timedelta(
            days=assistant.last_reactivation_date.weekday()
        )
        tracked_week_start = tracked_until - timedelta(days=tracked_until.weekday())
        elapsed_weeks = max(
            0,
            ((tracked_week_start - reactivation_week_start).days // 7) + 1,
        )
        expected_total_seconds = elapsed_weeks * assistant.weekly_hours * 3600
        all_sessions = TimeLog.objects.filter(
            assistant=assistant,
            check_out__isnull=False,
            check_in__date__gte=assistant.last_reactivation_date,
            check_in__date__lte=tracked_until,
        )
        cumulative_total_seconds = sum(
            max(
                0,
                int((session.check_out - session.check_in).total_seconds())
                - (session.break_minutes * 60),
            )
            for session in all_sessions
        )

        return Response(
            {
                'ok': True,
                'period': period,
                'period_start': period_start,
                'period_end': period_end,
                'total_seconds': total_seconds,
                'sessions': serializer.data,
                'cumulative_total_seconds': cumulative_total_seconds,
                'expected_total_seconds': expected_total_seconds,
                'deficit_seconds': cumulative_total_seconds - expected_total_seconds,
            },
            status=status.HTTP_200_OK,
        )


class WorkSessionReportsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assistant = request.user.assistant
        except Exception:
            return Response({'ok': True, 'total_seconds': 0, 'results': []})

        queryset = TimeLog.objects.filter(
            assistant=assistant,
            check_out__isnull=False,
        ).select_related('project', 'manager_user', 'status')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            if start_date:
                queryset = queryset.filter(check_in__date__gte=date.fromisoformat(start_date))
            if end_date:
                queryset = queryset.filter(check_in__date__lte=date.fromisoformat(end_date))
        except ValueError:
            return Response(
                {'detail': 'Las fechas deben usar el formato YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TimeLogSerializer(queryset.order_by('-check_in'), many=True)
        total_seconds = sum(
            max(0, item['elapsed_seconds'] - item['break_minutes'] * 60)
            for item in serializer.data
        )
        return Response({
            'ok': True,
            'total_seconds': total_seconds,
            'results': serializer.data,
        })


class AdminAssistantReportsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, assistant_id):
        if not Assistant.objects.filter(pk=assistant_id).exists():
            return Response(
                {'detail': 'Asistente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        input_serializer = AdminTimeLogSerializer(data=request.data, partial=True)
        input_serializer.is_valid(raise_exception=True)
        closed_status, _ = TimeLogStatus.objects.get_or_create(
            code='CLOSED',
            defaults={'is_final': True},
        )
        now = timezone.now()
        validated_data = input_serializer.validated_data
        time_log = TimeLog.objects.create(
            assistant_id=assistant_id,
            check_in=validated_data.pop('check_in', now),
            check_out=validated_data.pop('check_out', now),
            status=closed_status,
            **validated_data,
        )
        serializer = AdminTimeLogSerializer(time_log)
        return Response({'ok': True, 'report': serializer.data}, status=status.HTTP_201_CREATED)

    def get_queryset(self, assistant_id):
        return TimeLog.objects.filter(
            assistant_id=assistant_id,
            check_out__isnull=False,
        ).select_related('project', 'manager_user', 'status').order_by('-check_in')

    def get(self, request, assistant_id):
        queryset = self.get_queryset(assistant_id)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            if start_date:
                queryset = queryset.filter(check_in__date__gte=date.fromisoformat(start_date))
            if end_date:
                queryset = queryset.filter(check_in__date__lte=date.fromisoformat(end_date))
        except ValueError:
            return Response(
                {'detail': 'Las fechas deben usar el formato YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminTimeLogSerializer(queryset, many=True)
        total_seconds = sum(
            max(0, item['elapsed_seconds'] - item['break_minutes'] * 60)
            for item in serializer.data
        )
        return Response({
            'ok': True,
            'total_seconds': total_seconds,
            'results': serializer.data,
        })

    def patch(self, request, assistant_id):
        time_log_id = request.data.get('id')
        time_log = self.get_queryset(assistant_id).filter(id=time_log_id).first()
        if time_log is None:
            return Response({'detail': 'Reporte no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminTimeLogSerializer(time_log, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'report': serializer.data})

    def delete(self, request, assistant_id):
        time_log_id = request.data.get('id')
        time_log = self.get_queryset(assistant_id).filter(id=time_log_id).first()
        if time_log is None:
            return Response({'detail': 'Reporte no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        time_log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminReportsView(AdminAssistantReportsView):
    def get_queryset(self, assistant_id=None):
        return TimeLog.objects.filter(
            check_out__isnull=False,
        ).select_related(
            'assistant__user',
            'project',
            'manager_user',
            'status',
        ).order_by('-check_in')

    def get(self, request):
        queryset = self.get_queryset()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            if start_date:
                queryset = queryset.filter(check_in__date__gte=date.fromisoformat(start_date))
            if end_date:
                queryset = queryset.filter(check_in__date__lte=date.fromisoformat(end_date))
        except ValueError:
            return Response(
                {'detail': 'Las fechas deben usar el formato YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminTimeLogSerializer(queryset, many=True)
        total_seconds = sum(
            max(0, item['elapsed_seconds'] - item['break_minutes'] * 60)
            for item in serializer.data
        )
        return Response({
            'ok': True,
            'total_seconds': total_seconds,
            'results': serializer.data,
        })

    def patch(self, request):
        time_log = self.get_queryset().filter(id=request.data.get('id')).first()
        if time_log is None:
            return Response({'detail': 'Reporte no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminTimeLogSerializer(time_log, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'report': serializer.data})

    def delete(self, request):
        time_log = self.get_queryset().filter(id=request.data.get('id')).first()
        if time_log is None:
            return Response({'detail': 'Reporte no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        time_log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)