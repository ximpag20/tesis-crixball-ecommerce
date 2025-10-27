from django.db import models

class VisitCounter(models.Model):
    count = models.PositiveIntegerField(default=0)  # Contador de visitas

    def __str__(self):
        return str(self.count)
