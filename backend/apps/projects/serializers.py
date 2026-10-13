from rest_framework import serializers

from apps.projects.models import Project
from apps.users.models import User


class ActiveProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']


class ProjectAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'is_active']
        read_only_fields = ['id']


class ActiveCoordinatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'username']