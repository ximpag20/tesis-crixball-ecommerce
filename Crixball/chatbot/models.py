from django.db import models
from registro.models import Usuario

class MensajeChat(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    emisor = models.CharField(max_length=10, choices=[("usuario", "usuario"), ("bot", "bot")])
    contenido = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        db_table = 'historial_chat'

    def __str__(self):
        return f"{self.usuario.email} - {self.emisor}: {self.contenido[:30]}"
