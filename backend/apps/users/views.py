from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from core.permissions import IsAdmin, IsAdminOrCoordinator, IsFromInstitute 

from .models import AllowedIPRange, Assistant, User
from apps.schedules.models import Schedule
from apps.projects.models import Project
from .serializers import (
    AllowedIPRangeSerializer,
    AssistantCreateSerializer,
    AssistantListSerializer,
    AssistantAdminSerializer,
    CoordinatorCreateSerializer,
    CoordinatorAdminSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    AssistantDetailSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    PasswordResetConfirmSerializer,
)

from .services import validate_institute_ip_addr, change_user_password
from .recovery import request_password_reset, reset_password, verify_password_reset


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def validate_institute_ip_addr_view(request):
    result = validate_institute_ip_addr(request)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    return Response({'detail': 'Sesión cerrada correctamente'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        request_password_reset(serializer.validated_data['username'], request),
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_verify_view(request):
    serializer = PasswordResetVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    token = verify_password_reset(
        serializer.validated_data['username'],
        serializer.validated_data['code'],
    )
    if token is None:
        return Response(
            {'detail': 'El código no es válido o ya no está disponible.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({'ok': True, 'reset_token': token}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if not reset_password(
        serializer.validated_data['reset_token'],
        serializer.validated_data['new_password'],
    ):
        return Response(
            {'detail': 'La autorización de restablecimiento no es válida o expiró.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {'ok': True, 'detail': 'Contraseña restablecida correctamente.'},
        status=status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response({'ok': True, 'user': UserSerializer(request.user).data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrCoordinator])
def create_assistant_view(request):
    serializer = AssistantCreateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    assistant = serializer.save()

    return Response(
        {
            'ok': True,
            'assistant': AssistantDetailSerializer(assistant).data,        
        },
        status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrCoordinator])
def list_assistants_view(request):
    queryset = Assistant.objects.select_related('user').order_by('user__full_name')
    serializer = AssistantListSerializer(queryset, many=True)
    return Response({'ok': True, 'results': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_coordinators_view(request):
    if request.method == 'POST':
        serializer = CoordinatorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({'ok': True, 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)

    users = User.objects.select_related('role').filter(
        role__code__in=['coordinador', 'coordinator'],
    ).order_by('full_name', 'username')
    return Response(
        {'ok': True, 'results': CoordinatorAdminSerializer(users, many=True).data},
        status=status.HTTP_200_OK,
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_coordinator_detail_view(request, coordinator_id):
    coordinator = User.objects.filter(
        id=coordinator_id,
        role__code__in=['coordinador', 'coordinator'],
    ).first()
    if coordinator is None:
        return Response({'detail': 'Coordinador no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CoordinatorAdminSerializer(coordinator, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'ok': True, 'user': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_assistant_detail_view(request, assistant_id):
    assistant = Assistant.objects.select_related('user').filter(user_id=assistant_id).first()
    if assistant is None:
        return Response({'detail': 'Asistente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        serializer = AssistantAdminSerializer(
            assistant,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

    schedule = Schedule.objects.filter(assistant=assistant).prefetch_related('blocks').order_by('-valid_from').first()
    data = AssistantAdminSerializer(assistant).data
    data['schedule_blocks'] = [
        {
            'day_of_week': block.day_of_week,
            'start_time': block.start_time.strftime('%H:%M'),
            'end_time': block.end_time.strftime('%H:%M'),
        }
        for block in schedule.blocks.all()
    ] if schedule else []
    return Response({'ok': True, 'assistant': data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_summary_view(request):
    return Response(
        {
            'ok': True,
            'active_users': User.objects.filter(is_active=True).count(),
            'active_assistants': Assistant.objects.filter(user__is_active=True).count(),
            'active_projects': Project.objects.filter(is_active=True).count(),
        },
        status=status.HTTP_200_OK,
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        change_user_password(
            request.user,
            serializer.validated_data['current_password'],
            serializer.validated_data['new_password'],
            serializer.validated_data.get('needs_password_change', False),
        )
    except Exception as exc:
        detail = getattr(exc, 'message_dict', None)
        if detail:
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'No se pudo cambiar la contraseña.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {'ok': True, 'detail': 'Contraseña actualizada correctamente.'},
        status=status.HTTP_200_OK
    )

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            from rest_framework.exceptions import ValidationError

            raise ValidationError('No puedes eliminar tu propio usuario.')
        instance.delete()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        return Response({'ok': True, 'user': UserSerializer(request.user).data}, status=status.HTTP_200_OK)


class AllowedIPRangeViewSet(viewsets.ModelViewSet):
    queryset = AllowedIPRange.objects.all().order_by('-is_active', 'network')
    serializer_class = AllowedIPRangeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
