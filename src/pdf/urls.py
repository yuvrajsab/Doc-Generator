from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from rest_framework import permissions
from drf_yasg2.views import get_schema_view
from drf_yasg2 import openapi
from django.conf.urls import url
from . import views

schema_view = get_schema_view(
    openapi.Info(
        title="Doc-Generator",
        default_version='v1',
        description="Doc-Generator API's",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="radhay@samagragovernance.in"),
        license=openapi.License(name="Test License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    url(r'^dmc/', include('data_mapping_console.urls')),
    path(r'ht/', include('health_check.urls')),
    path('grappelli/', include('grappelli.urls')),  # Admin grappelli URLS
    path('admin/', admin.site.urls),
    path('test-page/', views.current_datetime),
    path('register-user/', views.register_user_init),
    path('redirect/', views.register_user),
    url(r'^register/$', views.register_template, name='get_test'),
    path('generate/', views.generate_pdf2, name='get_pdf'),
    path('generateByTemplate/', views.generate_by_template, name='get_by_template'),
    path('bulk/generate/', views.generate_bulk, name='get_status'),
    path('bulk/generate/<uuid:token>/', views.generate_bulk, name='get_status'),
    url('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
