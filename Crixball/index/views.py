from django.shortcuts import render
from catalogo.models import Producto  # Asegúrate de que este es el nombre correcto de la app
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from registro.models import Usuario
from .forms import ActualizarDatosForm
from django.contrib.auth.hashers import make_password
from .forms import CambiarContrasenaForm
from registro.models import Usuario
from contactos.models import Comentario
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def Inicio(request):
    # Contamos la cantidad de usuarios registrados
    from registro.models import Usuario
    cantidad_usuarios = Usuario.objects.count()

    # Obtenemos 6 productos aleatorios
    productos = Producto.objects.order_by('?')[:6]
    comentarios = Comentario.objects.select_related('usuario').order_by('-fecha_creacion')[:6]
    
    # Título de la página
    tittle = 'Titulo'
    
    # Pasamos los productos y la cantidad de usuarios al contexto
    return render(request, 'index/index.html', {
        'title': tittle,
        'cantidad_usuarios': cantidad_usuarios,
        'productos': productos,  # Enviamos los productos al contexto
        'comentarios': comentarios,
    })

@login_required
def actualizar_datos(request):
    try:
        # Obtener el usuario actual
        usuario = Usuario.objects.get(email=request.user.username)
    except Usuario.DoesNotExist:
        return redirect("Inicio")

    success_message = None  # Variable para manejar el mensaje de éxito

    if request.method == "POST":
        # Crear una copia mutable del POST para manejar campos no modificados
        post_data = request.POST.copy()

        # Restaurar los valores originales en caso de que los campos estén vacíos
        if not post_data.get("nombre"):
            post_data["nombre"] = usuario.nombre

        if not post_data.get("apellido"):
            post_data["apellido"] = usuario.apellido

        if not post_data.get("email"):
            post_data["email"] = usuario.email

        if not post_data.get("tel"):
            post_data["tel"] = usuario.tel

        if not post_data.get("birth"):
            post_data["birth"] = usuario.birth

        # Usar la copia mutable para crear el formulario
        form = ActualizarDatosForm(post_data, instance=usuario)

        if form.is_valid():
            # Validar correo único
            nuevo_email = form.cleaned_data["email"]
            if nuevo_email != usuario.email and Usuario.objects.filter(email=nuevo_email).exists():
                form.add_error("email", "El correo electrónico ya está registrado por otro usuario.")
                return render(request, "index/actualizar_datos.html", {"form": form})

            # Validar teléfono único
            nuevo_tel = form.cleaned_data["tel"]
            if nuevo_tel != usuario.tel and Usuario.objects.filter(tel=nuevo_tel).exists():
                form.add_error("tel", "El número de teléfono ya está registrado por otro usuario.")
                return render(request, "index/actualizar_datos.html", {"form": form})

            # Guardar cambios
            form.save()
            success_message = "¡Tus datos han sido actualizados exitosamente!"  # Definir mensaje de éxito
        else:
            return render(request, "index/actualizar_datos.html", {"form": form})

    else:
        # Método GET: Renderizar formulario con valores iniciales
        form = ActualizarDatosForm(instance=usuario)

    return render(request, "index/actualizar_datos.html", {"form": form, "success_message": success_message})
@login_required
def actualizar_datos(request):
    try:
        # Obtener el usuario actual
        usuario = Usuario.objects.get(email=request.user.username)
    except Usuario.DoesNotExist:
        return redirect("Inicio")

    success_message = None  # Variable para manejar el mensaje de éxito

    if request.method == "POST":
        # Crear una copia mutable del POST para manejar campos no modificados
        post_data = request.POST.copy()

        # Restaurar los valores originales en caso de que los campos estén vacíos
        if not post_data.get("nombre"):
            post_data["nombre"] = usuario.nombre

        if not post_data.get("apellido"):
            post_data["apellido"] = usuario.apellido

        if not post_data.get("email"):
            post_data["email"] = usuario.email

        if not post_data.get("tel"):
            post_data["tel"] = usuario.tel

        if not post_data.get("birth"):
            post_data["birth"] = usuario.birth.strftime("%Y-%m-%d") if usuario.birth else ""

        # Usar la copia mutable para crear el formulario
        form = ActualizarDatosForm(post_data, instance=usuario)

        if form.is_valid():
            # Validar correo único
            nuevo_email = form.cleaned_data["email"]
            if nuevo_email != usuario.email and Usuario.objects.filter(email=nuevo_email).exists():
                form.add_error("email", "El correo electrónico ya está registrado por otro usuario.")
                return render(request, "index/actualizar_datos.html", {"form": form})

            # Validar teléfono único
            nuevo_tel = form.cleaned_data["tel"]
            if nuevo_tel != usuario.tel and Usuario.objects.filter(tel=nuevo_tel).exists():
                form.add_error("tel", "El número de teléfono ya está registrado por otro usuario.")
                return render(request, "index/actualizar_datos.html", {"form": form})

            # Guardar cambios
            form.save()
            success_message = "¡Tus datos han sido actualizados exitosamente!"  # Definir mensaje de éxito
        else:
            return render(request, "index/actualizar_datos.html", {"form": form})

    else:
        # Método GET: Renderizar formulario con valores iniciales
        form = ActualizarDatosForm(instance=usuario)

    return render(request, "index/actualizar_datos.html", {"form": form, "success_message": success_message})

@login_required
def cambiar_contrasena(request):
    usuario = Usuario.objects.get(email=request.user.username)  # Obtener usuario personalizado
    success_message = None  # Variable para manejar el mensaje de éxito

    if request.method == "POST":
        form = CambiarContrasenaForm(usuario, request.POST)
        if form.is_valid():
            # Actualizar la contraseña usando make_password para encriptar
            nueva_contrasena = form.cleaned_data["nueva_contrasena"]
            usuario.contrasenia = make_password(nueva_contrasena)  # Asegurar encriptación
            usuario.save()  # Guardar cambios
            success_message = "¡Tu contraseña ha sido cambiada exitosamente!"
            return render(request, "index/cambiar_contrasena.html", {"form": form, "success_message": success_message})
    else:
        form = CambiarContrasenaForm(usuario)

    return render(request, "index/cambiar_contrasena.html", {"form": form, "success_message": success_message})
