from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from core.permissions import IsAdmin

from apps.projects.models import Project
from apps.projects.serializers import (
    ActiveProjectSerializer,
    ActiveCoordinatorSerializer,
    ProjectAdminSerializer,
)
from apps.users.models import User


class ActiveProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Project.objects.filter(is_active=True).order_by('name')
        serializer = ActiveProjectSerializer(queryset, many=True)
        return Response({'ok': True, 'results': serializer.data})


class AdminProjectListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        queryset = Project.objects.all().order_by('name')
        if request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        serializer = ProjectAdminSerializer(queryset, many=True)
        return Response({'ok': True, 'results': serializer.data})

    def post(self, request):
        serializer = ProjectAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(
            {'ok': True, 'project': ProjectAdminSerializer(project).data},
            status=status.HTTP_201_CREATED,
        )


class AdminProjectDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, project_id):
        project = Project.objects.filter(id=project_id).first()
        if project is None:
            return Response(
                {'detail': 'Proyecto no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProjectAdminSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'project': serializer.data})


class ActiveCoordinatorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = User.objects.select_related('role').filter(
            is_active=True,
            role__code__in=['coordinador', 'coordinator'],
        ).order_by('full_name', 'username')
        serializer = ActiveCoordinatorSerializer(queryset, many=True)
        return Response({'ok': True, 'results': serializer.data})