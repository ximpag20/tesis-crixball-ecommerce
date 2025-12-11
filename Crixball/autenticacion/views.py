# autenticacion/views.py

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from registro.models import Usuario
from django.contrib.auth.models import User
from catalogo.saleor_user_service import SaleorUserService

def Autenticacion(request):
    if request.session.get('registro_exitoso'):
        messages.success(request, "Registro exitoso. Puedes iniciar sesión.")
        del request.session['registro_exitoso']

    if request.method == 'POST':
        email = request.POST['email']
        contrasena = request.POST['contrasena']
        next_url = request.POST.get('next', 'Inicio')

        # 🔥 AUTENTICAR CONTRA SALEOR
        user_service = SaleorUserService()
        resultado = user_service.autenticar_usuario_saleor(email, contrasena)
        
        if not resultado:
            messages.error(request, "Credenciales incorrectas")
            return redirect('Autenticacion')
        
        # 🔥 Obtener datos del usuario de Saleor
        usuario_saleor = resultado['user']
        token_saleor = resultado['token']
        refresh_token = resultado['refreshToken']
        
        print(f"✅ Usuario autenticado en Saleor: {email}")
        print(f"🔑 Token: {token_saleor}")
        
        # Buscar datos adicionales en Django (CI, teléfono, fecha de nacimiento)
        try:
            usuario_django = Usuario.objects.get(email=email)
            ci = usuario_django.ci
            tel = usuario_django.tel
            birth = usuario_django.birth.strftime('%Y-%m-%d')
        except Usuario.DoesNotExist:
            # Si no existe en Django, usar valores por defecto
            ci = "N/A"
            tel = "N/A"
            birth = "N/A"
        
        # Crear usuario de Django para la sesión (sin validar contraseña)
        django_user, created = User.objects.get_or_create(username=email)
        if created:
            django_user.set_unusable_password()  # No necesitamos contraseña en Django
            django_user.save()
        
        # Autenticar sesión de Django (sin validar contraseña)
        django_user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, django_user)

        # 🔥 Guardar información de Saleor en sesión
        request.session['correo_usuario'] = usuario_saleor['email']
        request.session['nombre_usuario'] = usuario_saleor['firstName']
        request.session['apellido_usuario'] = usuario_saleor['lastName']
        request.session['CI_usuario'] = ci
        request.session['birth_usuario'] = birth
        request.session['tel_usuario'] = tel
        request.session['etiqueta'] = "Reservaciones"
        
        # 🔥 IMPORTANTE: Guardar tokens de Saleor
        request.session['saleor_token'] = token_saleor
        request.session['saleor_refresh_token'] = refresh_token
        request.session['saleor_user_id'] = usuario_saleor['id']

        # Asignar rol
        if email == "paguayximena4@gmail.com":
            request.session['rol_usuario'] = "administrador"
        else:
            request.session['rol_usuario'] = "usuario"

        return redirect(next_url)

    return redirect('Inicio')