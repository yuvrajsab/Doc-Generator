from django.urls import path
from django.conf.urls import include
from django.conf.urls import url
from . import views

urlpatterns = [
    path('templates/', views.getAllConfigurations),
    path('templates/<int:config_id>/', views.configurationOp),
    path('templates/<int:config_id>/preview/', views.preview),
    path('odk/forms/', views.getODKForms),
    path('odk/forms/<str:form_id>/', views.parseODKForm),
    path('login/', views.login),
]
