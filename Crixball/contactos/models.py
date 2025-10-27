from django.db import models
from registro.models import Usuario  # <-- para la relación con Usuario

class Comentario(models.Model):
    id = models.AutoField(primary_key=True)
    tema = models.CharField(max_length=255)
    subtema = models.CharField(max_length=255, null=True, blank=True)
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, to_field='ci', on_delete=models.CASCADE, db_column='usuario_ci', null=True, blank=True)

    class Meta:
        db_table = "contactos_comentario"  # <- así respeta tu tabla existente

    def __str__(self):
        return f"{self.tema} - {self.subtema}"
