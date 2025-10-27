from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Usuario
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

def validar_CI_ecuador(ci):
    """Valida el formato de la cédula ecuatoriana."""
    if len(ci) != 10 or not ci.isdigit():
        return False

    verificador = int(ci[-1])
    cis_without_verifier = int(ci[:-1])
    
    suma = 0
    for i in range(9):
        digito = cis_without_verifier % 10
        cis_without_verifier //= 10

        if i % 2 == 0:
            digito *= 2
            if digito > 9:
                digito -= 9
        
        suma += digito

    digito_verificador_esperado = 10 - (suma % 10)
    if digito_verificador_esperado == 10:
        digito_verificador_esperado = 0

    return verificador == digito_verificador_esperado

def Registro(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '')
        apellido = request.POST.get('apellido', '')
        ci = request.POST.get('CI', '')
        tel = request.POST.get('tel', '')
        email = request.POST.get('email', '')
        contrasena = request.POST.get('contrasena', '')
        confirmar_contrasena = request.POST.get('confirmar_contrasena', '')
        birth = request.POST.get('birth', '')

        # Validaciones
        errores = []

        # Verificar campos vacíos
        if not all([nombre, apellido, ci, tel, email, contrasena, confirmar_contrasena, birth]):
            errores.append("Por favor, rellena todos los campos.")

        # Validar cédula ecuatoriana
        if not validar_CI_ecuador(ci):
            errores.append("La cédula ingresada no es válida.")

        # Validar coincidencia de contraseñas
        if contrasena != confirmar_contrasena:
            errores.append("Las contraseñas no coinciden.")

        # Validar contraseña fuerte
        try:
            validate_password(contrasena)
        except ValidationError as e:
            errores.extend(e.messages)

        # Verificar duplicados en la base de datos
        if Usuario.objects.filter(ci=ci).exists():
            errores.append("La cédula ya está registrada.")
        if Usuario.objects.filter(email=email).exists():
            errores.append("El correo ya está registrado.")
        if Usuario.objects.filter(tel=tel).exists():
            errores.append("El teléfono ya está registrado.")

        # Devolver errores si existen
        if errores:
            return JsonResponse({"success": False, "errors": errores})

        # Crear usuario
        usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            ci=ci,
            tel=tel,
            email=email,
            contrasenia=make_password(contrasena),
            birth=birth,
        )
        usuario.save()
        return JsonResponse({
            "success": True,
            "message": "Usuario registrado exitosamente. Ahora puedes iniciar sesión."
        })

    return JsonResponse({"success": False, "errors": ["Método no permitido."]})
