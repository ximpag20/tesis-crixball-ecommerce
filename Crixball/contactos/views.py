from django.shortcuts import render
from .models import Comentario
from django.http import JsonResponse
import os
from registro.models import Usuario
from django.contrib.auth.decorators import login_required
from citas.models import Notification 

def Contacto(request):
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    return render(request, 'contactos/index.html', {
        'GOOGLE_MAPS_API_KEY': google_maps_api_key
    })

@login_required
def Comentarios(request):
    if request.method == "POST":
        tema = request.POST.get("tema")
        subtema = request.POST.get("subtema", "")
        comentario = request.POST.get("comentario")

        if tema and comentario:
            email_usuario = request.user.username
            try:
                usuario = Usuario.objects.get(email=email_usuario)  # Buscar usuario por email

                # Crear el comentario
                comentario_guardado = Comentario.objects.create(
                    tema=tema,
                    subtema=subtema,
                    comentario=comentario,
                    usuario=usuario  # Aquí Django automáticamente asigna usuario_ci con el CI
                )

                # Crear notificación para el administrador
                # Asumimos que el administrador tiene el email 'admin@example.com' (puedes cambiarlo según lo necesites)
                admin_user = Usuario.objects.get(email="arielvela8910@gmail.com")

                # Crear la notificación para el administrador
                Notification.objects.create(
                    user=admin_user,
                    message=f"El cliente {usuario.nombre} {usuario.apellido} envió un comentario: {tema}",
                    link="/contactos/ver_comentarios"  # Enlace a la página donde el admin puede ver los comentarios
                )

                return JsonResponse({"message": "Comentario enviado correctamente"}, status=200)

            except Usuario.DoesNotExist:
                return JsonResponse({"error": "Usuario no encontrado"}, status=400)

        else:
            return JsonResponse({"error": "Faltan campos obligatorios"}, status=400)

    return render(request, "contactos/comentarios.html")

@login_required
def ver_comentarios(request):
    comentarios = Comentario.objects.select_related('usuario').order_by('-fecha_creacion')
    return render(request, 'contactos/ver_comentarios.html', {
        'comentarios': comentarios
    })