from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Contacto, name='Contacto'),
    path ('comentarios/', views.Comentarios, name='comentarios'),
    path('ver_comentarios/', views.ver_comentarios, name='ver_comentarios'),
]