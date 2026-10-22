from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin

from apps.users.models import User

from .models import Request
from .serializers import AdminOptionSerializer, RequestSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_options_view(request):
    admins = User.objects.filter(is_admin=True, is_active=True).order_by('full_name', 'username')
    return Response({'ok': True, 'results': AdminOptionSerializer(admins, many=True).data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def requests_view(request):
    if request.method == 'POST':
        if request.user.is_admin or not request.user.role or request.user.role.code != 'asistente':
            return Response(
                {'detail': 'Solo los asistentes pueden crear solicitudes.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request_instance = serializer.save()
        return Response(
            {'ok': True, 'request': RequestSerializer(request_instance).data},
            status=status.HTTP_201_CREATED,
        )

    if request.user.is_admin:
        queryset = Request.objects.filter(admin=request.user)
    else:
        queryset = Request.objects.filter(assistant=request.user)

    attended = request.query_params.get('attended')
    if attended in ('true', 'false'):
        queryset = queryset.filter(is_attended=attended == 'true')
    queryset = queryset.select_related('admin', 'assistant', 'report', 'report__project')
    return Response({'ok': True, 'results': RequestSerializer(queryset, many=True).data})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def request_detail_view(request, request_id):
    request_instance = Request.objects.select_related(
        'admin', 'assistant', 'report', 'report__project',
    ).filter(id=request_id).first()
    if request_instance is None:
        return Response({'detail': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_admin:
        allowed = request_instance.admin_id == request.user.id
    else:
        allowed = request_instance.assistant_id == request.user.id
    if not allowed:
        return Response({'detail': 'No tienes permiso para consultar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        if not request.user.is_admin or request_instance.admin_id != request.user.id:
            return Response({'detail': 'Solo el administrador asignado puede atender la solicitud.'}, status=status.HTTP_403_FORBIDDEN)
        if request.data.get('is_attended') is not True:
            return Response({'detail': 'La solicitud solo puede marcarse como atendida.'}, status=status.HTTP_400_BAD_REQUEST)
        request_instance.mark_attended()

    return Response({'ok': True, 'request': RequestSerializer(request_instance).data})
