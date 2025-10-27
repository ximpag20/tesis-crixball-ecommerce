from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Acerca, name='Acerca'),
]