from django.apps import AppConfig
import catalogo.signals

class CatalogoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogo'
    
    def ready(self):
        import catalogo.signals  # Importar los signals cuando la app esté lista
        """
        Método que se ejecuta cuando Django inicia.
        Aquí importamos los signals para que se registren.
        """
          # Importar signals para registrarlos
