from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from chatbot.models import MensajeChat
from registro.models import Usuario

@receiver(user_logged_out)
def borrar_chat_al_cerrar_sesion(sender, request, user, **kwargs):
    try:
        usuario = Usuario.objects.get(email=user.username)
        MensajeChat.objects.filter(usuario=usuario).delete()
        print(f"🧹 Chat eliminado para {usuario.email}")
    except Usuario.DoesNotExist:
        print("⚠️ Usuario no encontrado al cerrar sesión.")
