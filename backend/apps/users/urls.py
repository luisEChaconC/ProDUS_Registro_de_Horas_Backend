from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AllowedIPRangeViewSet,
    CustomTokenObtainPairView,
    UserViewSet,
    list_assistants_view,
    logout_view,
    me_view,
    validate_institute_ip_addr_view,
    create_assistant_view,
    change_password_view,
    admin_summary_view,
    admin_assistant_detail_view,
    admin_coordinators_view,
    admin_coordinator_detail_view,
    password_reset_request_view,
    password_reset_verify_view,
    password_reset_confirm_view,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'allowed-ip-ranges', AllowedIPRangeViewSet, basename='allowed-ip-range')

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/me/', me_view, name='auth_me'),
    path('auth/validate-institute-ip/', validate_institute_ip_addr_view, name='validate_institute_ip_addr'),
    path('auth/password-reset/request/', password_reset_request_view, name='password_reset_request'),
    path('auth/password-reset/verify/', password_reset_verify_view, name='password_reset_verify'),
    path('auth/password-reset/confirm/', password_reset_confirm_view, name='password_reset_confirm'),
    path('assistants/', create_assistant_view, name='create_assistant'),
    path('assistants/create/', create_assistant_view, name='create_assistant_legacy'),
    path('assistants/list/', list_assistants_view, name='list_assistants'),
    path('admin/summary/', admin_summary_view, name='admin_summary'),
    path('admin/assistants/<int:assistant_id>/', admin_assistant_detail_view, name='admin_assistant_detail'),
    path('admin/coordinators/', admin_coordinators_view, name='admin_coordinators'),
    path('admin/coordinators/<int:coordinator_id>/', admin_coordinator_detail_view, name='admin_coordinator_detail'),
    path('change-password/', change_password_view, name='change_password'),
    path('', include(router.urls)),
]
