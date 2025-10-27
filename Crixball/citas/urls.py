from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Citas, name='Citas'),
    path('reservascliente/', views.listar_reservas, name='reservas_cliente'),
    path('todas-reservas/', views.ver_todas_reservas, name='ver_todas_reservas'),
    path('citas/hoy/', views.ver_reservas_hoy, name='reservas_hoy'),
    path('calendario/', views.calendario_reservas, name='calendario_reservas'),
    path('obtener_reservas/', views.obtener_reservas, name='obtener_reservas'),
    path('verificar-horas-ocupadas/', views.verificar_horas_ocupadas, name='verificar_horas_ocupadas'),
    path('notificaciones/marcar-leida/<int:notificacion_id>/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificaciones/obtener/', views.obtener_notificaciones, name='obtener_notificaciones'),
    path('verificar-reserva/', views.verificar_reserva, name='verificar_reserva'),
    path('eliminar-reserva/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
]