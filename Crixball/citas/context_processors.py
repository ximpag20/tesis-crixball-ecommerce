
from .models import Notification
from registro.models import Usuario

def notifications_context(request):
    if request.user.is_authenticated:
        try:
            # Buscar al usuario en `Usuario` usando el `username`
            usuario = Usuario.objects.get(email=request.user.username)  # Aquí se usa `username` como `email`

            # Consulta separada para notificaciones no leídas
            notificaciones_no_leidas = Notification.objects.filter(user=usuario, is_read=False)
            
            # Consulta para las últimas 5 notificaciones
            notificaciones = Notification.objects.filter(user=usuario).order_by('-created_at')[:5]
            
            return {
                'notificaciones': notificaciones,
                'notificaciones_no_leidas': notificaciones_no_leidas,
            }
        except Usuario.DoesNotExist:
            return {}  # Usuario no existe en `Usuario`, retornar un contexto vacío
    return {}
