from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from registro.models import Usuario
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User

def Autenticacion(request):
    if request.session.get('registro_exitoso'):
        messages.success(request, "Registro exitoso. Puedes iniciar sesión.")
        del request.session['registro_exitoso']

    if request.method == 'POST':
        email = request.POST['email']
        contrasena = request.POST['contrasena']
        next_url = request.POST.get('next', 'Inicio')  # URL de redirección tras login

        try:
            # Buscar el usuario en tu modelo personalizado
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            messages.error(request, "Credenciales incorrectas")
            return redirect('Autenticacion')

        # Verificar contraseña con check_password
        if check_password(contrasena, usuario.contrasenia):
            # Crear un usuario de Django temporal si no existe
            django_user, created = User.objects.get_or_create(username=email)
            
            # Evitar resetear la contraseña si el usuario ya existe
            if created:
                django_user.set_password(contrasena)
                django_user.save()

            # Autenticar usuario y establecer sesión
            login(request, django_user)

            # Configurar variables de sesión
            request.session['correo_usuario'] = usuario.email
            request.session['nombre_usuario'] = usuario.nombre
            request.session['apellido_usuario'] = usuario.apellido
            request.session['CI_usuario'] = usuario.ci
            request.session['birth_usuario'] = usuario.birth.strftime('%Y-%m-%d')
            request.session['tel_usuario'] = usuario.tel
            request.session['etiqueta'] = "Reservaciones"

            # Asignar rol de usuario
            if email == "paguayximena4@gmail.com":
                request.session['rol_usuario'] = "administrador"
            else:
                request.session['rol_usuario'] = "usuario"

            return redirect(next_url)

        else:
            messages.error(request, "Contraseña incorrecta")
            return redirect('Autenticacion')

    return redirect('Inicio')
