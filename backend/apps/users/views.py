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
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    AssistantDetailSerializer,
)

from .services import validate_institute_ip_addr, change_user_password


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def validate_institute_ip_addr_view(request):
    result = validate_institute_ip_addr(request)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    return Response({'detail': 'Sesión cerrada correctamente'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response({'ok': True, 'user': UserSerializer(request.user).data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrCoordinator])
def create_assistant_view(request):
    serializer = AssistantCreateSerializer(data=request.data)
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
