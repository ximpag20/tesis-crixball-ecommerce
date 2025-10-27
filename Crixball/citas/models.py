from django.db import models
from registro.models import Usuario
from catalogo.models import Producto, Talla
from django.contrib.auth.models import User

class Reserva(models.Model):
    id_reserva = models.AutoField(primary_key=True)
    ci = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='ci')
    id_pro = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, db_column='id_pro')
    talla = models.ForeignKey(Talla, on_delete=models.SET_NULL, null=True, db_column='id_talla')  # Nueva relación
    cantidad_reservada = models.PositiveIntegerField()
    date_reserva = models.DateField()
    hora_reserva = models.TimeField()
    comentario = models.TextField(blank=True, null=True)
    estado_reserva = models.CharField(max_length=50, default='Pendiente')

    def __str__(self):
        return f"Reserva {self.id_reserva} - {self.ci} - {self.id_pro} - {self.talla}"
    
    class Meta:
        db_table = 'reservas'

class Notification(models.Model):
    user = models.ForeignKey(Usuario, on_delete=models.CASCADE)  # Usuario que recibe la notificación
    message = models.TextField()  # Mensaje de la notificación
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    is_read = models.BooleanField(default=False)  # Estado de lectura
    link = models.URLField(blank=True, null=True)  # Enlace al que dirige la notificación

    def __str__(self):
        return f"Notification for {self.user.email} - {self.message}"
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']  # Ordenar por las más recientes primero