from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Inicio, name='Inicio'),
    path("actualizar_datos/", views.actualizar_datos, name="actualizar_datos"),
    path('cambiar_contrasena/', views.cambiar_contrasena, name='cambiar_contrasena'),
]