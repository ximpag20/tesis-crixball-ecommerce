from django.db import models

class Usuario(models.Model):
    ci = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    email = models.EmailField(unique=True, max_length=50)
    tel = models.CharField(max_length=10, unique=True)
    contrasenia = models.CharField(max_length=100)
    birth = models.DateField()

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    class Meta:
        db_table = 'usuarios'  # Especifica el nombre exacto de la tabla en PostgreSQL
