from django.shortcuts import render
from catalogo.models import Producto  # Asegúrate de que este es el nombre correcto de la app
from .models import VisitCounter

def Acerca(request):
    # Contamos la cantidad de usuarios registrados
    from registro.models import Usuario
    cantidad_usuarios = Usuario.objects.count()

    # Obtener o crear el contador de visitas
    counter, created = VisitCounter.objects.get_or_create(id=1)  # Usamos un único objeto con ID=1
    counter.count += 1  # Incrementamos el contador
    counter.save()  # Guardamos los cambios

    return render(request, 'acerca/index.html', {
        'cantidad_usuarios': cantidad_usuarios,
        'visit_count': counter.count,  # Pasamos el contador al contexto
    })
