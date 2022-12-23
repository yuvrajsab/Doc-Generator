from django.urls import path
from django.conf.urls import include
from django.conf.urls import url
from . import views

urlpatterns = [
    path('templates/', views.getAllConfigurations),
    path('templates/<int:id>/', views.configurationOp),
    # path(r'ht/', include('health_check.urls')),
    # path('grappelli/', include('grappelli.urls')),  # Admin grappelli URLS
    # path('admin/', admin.site.urls),
    # path('test-page/', views.current_datetime),
    # path('register-user/', views.register_user_init),
    # path('redirect/', views.register_user),
    # url(r'^register/$', views.register_template, name='get_test'),
    # path('generate/', views.generate_pdf2, name='get_pdf'),
    # path('generateByTemplate/', views.generate_by_template, name='get_by_template'),
    # path('bulk/generate/', views.generate_bulk, name='get_status'),
    # path('bulk/generate/<uuid:token>/', views.generate_bulk, name='get_status'),
    # url('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # url('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
