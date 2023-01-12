from django.urls import path
from django.conf.urls import include
from django.conf.urls import url
from . import views

urlpatterns = [
    path('configurations/', views.getAllConfigurations),
    path('configurations/<int:config_id>/', views.configurationOp),
    path('configurations/<int:config_id>/preview/', views.preview),
    path('odk/forms/', views.getODKForms),
    path('odk/forms/<str:form_id>/', views.parseODKForm),
    path('login/', views.login),
]
