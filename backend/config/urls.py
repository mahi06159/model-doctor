from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from audits.views import AuditJobViewSet, PreviewDatasetView, ReportDownloadView, DemoAuditsView


class HealthCheckView(APIView):
    """
    Protected Health Check View.
    Used to verify JWT validation. Returns basic information about the authenticated user.
    """
    def get(self, request):
        return Response({
            "status": "healthy",
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
            }
        })


router = DefaultRouter()
router.register(r'audits', AuditJobViewSet, basename='audit')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Protected diagnostic endpoint
    path('api/health-check/', HealthCheckView.as_view(), name='health_check'),
    
    # Columns preview endpoint
    path('api/audits/preview-dataset/', PreviewDatasetView.as_view(), name='preview_dataset'),
    
    # Report download endpoint (changed uuid to str to support demo- prefixed strings)
    path('api/audits/<str:job_id>/report/', ReportDownloadView.as_view(), name='audit_report'),
    
    # Public demo audits endpoints
    path('api/demo-audits/', DemoAuditsView.as_view(), name='demo_audits_list'),
    path('api/demo-audits/<str:job_id>/', DemoAuditsView.as_view(), name='demo_audits_detail'),
    
    # Audits API routes
    path('api/', include(router.urls)),
]

# Serve uploaded media files locally in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
