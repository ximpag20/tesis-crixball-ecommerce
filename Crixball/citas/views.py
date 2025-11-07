from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from catalogo.models import Producto,ProductoTalla
from .forms import ReservaForm
from .models import Reserva, Talla, Notification
from registro.models import Usuario

from datetime import date

from django.http import JsonResponse
from datetime import datetime,timedelta

from django.db.models import Prefetch


@login_required
def Citas(request):
    # Obtener el usuario autenticado
    email_usuario = request.user.username
    try:
        usuario = Usuario.objects.get(email=email_usuario)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado en el sistema. Contacta al administrador.", extra_tags='reserva')
        return render(request, 'citas/index.html', {'form': None, 'productos': None})

    # Prefetch de ProductoTalla para optimizar consultas
    productos = Producto.objects.prefetch_related(
        Prefetch('producto_tallas', queryset=ProductoTalla.objects.filter(cantidad_disponible__gt=0))
    )

    producto_seleccionado = None

    # Manejo del parámetro `producto_id` desde la URL
    producto_id = request.GET.get('producto_id')  # Capturar desde la URL
    if producto_id:
        try:
            producto_seleccionado = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            messages.error(request, "El producto seleccionado no existe.", extra_tags='reserva')

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.ci = usuario

            # Convertir id_pro en una instancia de Producto
            producto_id = form.cleaned_data.get('id_pro')
            try:
                producto = Producto.objects.get(pk=producto_id.id_pro)
                reserva.id_pro = producto
            except Producto.DoesNotExist:
                messages.error(request, "El producto seleccionado no existe.", extra_tags='reserva')
                return redirect('Citas')

            # Convertir talla en una instancia de Talla
            talla_nombre = form.cleaned_data.get('talla')
            try:
                talla_obj = Talla.objects.get(talla=talla_nombre)  # Convertir talla a instancia
                reserva.talla = talla_obj
            except Talla.DoesNotExist:
                messages.error(request, "La talla seleccionada no existe.", extra_tags='reserva')
                return redirect('Citas')

            # Validar la cantidad reservada
            try:
                producto_talla = producto.producto_tallas.get(talla=talla_obj)
            except ProductoTalla.DoesNotExist:
                messages.error(request, "La talla seleccionada no tiene stock disponible.", extra_tags='reserva')
                return redirect('Citas')

            if reserva.cantidad_reservada > producto_talla.cantidad_disponible:
                messages.error(request, "Cantidad insuficiente del producto seleccionado.", extra_tags='reserva')
            else:
                # Actualizar cantidad disponible y guardar reserva
                producto_talla.cantidad_disponible -= reserva.cantidad_reservada
                producto_talla.save()

                producto_talla.sincronizar_stock_con_saleor()

                reserva.estado_reserva = "Pendiente"
                reserva.save()

                # Crear notificación para el administrador estático
                try:
                    admin_user = Usuario.objects.get(email="arielvela8910@gmail.com")
                    Notification.objects.create(
                        user=admin_user,
                        message=f"El cliente {usuario.nombre} {usuario.apellido} hizo una nueva reserva.",
                        link="/citas/todas-reservas/"
                    )
                except Usuario.DoesNotExist:
                    messages.error(request, "El administrador no está registrado en el sistema.", extra_tags='reserva')

                messages.success(request, "¡Reserva realizada con éxito!", extra_tags='reserva')
                return redirect('Citas')
        else:
            # Mostrar errores específicos del formulario
            messages.error(request, "Por favor, corrige los errores en el formulario.", extra_tags='reserva')
    else:
        # Inicializar el formulario con el producto preseleccionado
        initial_data = {'id_pro': producto_id} if producto_id else {}
        form = ReservaForm(initial=initial_data)

    # Renderizar la plantilla con los datos necesarios
    return render(request, 'citas/index.html', {
        'form': form,
        'productos': productos,
        'producto_seleccionado': producto_seleccionado,
    })



@login_required
def listar_reservas(request):
    """Vista para mostrar y eliminar reservas del usuario actual."""
    email_usuario = request.user.username
    try:
        usuario = Usuario.objects.get(email=email_usuario)
    except Usuario.DoesNotExist:
        messages.error(request, "Usuario no encontrado en el sistema.", extra_tags='reservas_cliente')
        return render(request, 'citas/reservas_cliente.html', {'reservas': None})

    # Obtener las reservas del usuario autenticado
    reservas = Reserva.objects.filter(ci=usuario).select_related('id_pro', 'talla')

    # Agregar precio unitario y total a cada reserva
    for reserva in reservas:
        try:
            producto_talla = ProductoTalla.objects.get(producto=reserva.id_pro, talla=reserva.talla)
            reserva.precio_unitario = producto_talla.precio  # Precio unitario
            reserva.total = producto_talla.precio * reserva.cantidad_reservada  # Total
        except ProductoTalla.DoesNotExist:
            reserva.precio_unitario = None
            reserva.total = None

    # Lógica para cancelar una reserva
    if request.method == 'POST' and 'cancelar_id' in request.POST:
        reserva_id = request.POST['cancelar_id']
        reserva = get_object_or_404(Reserva, id_reserva=reserva_id, ci=usuario)

        # Verificar que la reserva no esté confirmada
        if reserva.estado_reserva == "Confirmada":
            messages.error(request, "No puedes cancelar una reserva confirmada.", extra_tags='reservas_cliente')
        else:
            # Devolver la cantidad reservada al inventario si no está confirmada
            producto_talla = ProductoTalla.objects.get(producto=reserva.id_pro, talla=reserva.talla)
            producto_talla.cantidad_disponible += reserva.cantidad_reservada
            producto_talla.save()

            producto_talla.sincronizar_stock_con_saleor()
            
            # Eliminar la reserva
            reserva.delete()
            messages.success(request, "Reserva cancelada exitosamente.", extra_tags='reservas_cliente')

        return redirect('reservas_cliente')

    return render(request, 'citas/reservas_cliente.html', {'reservas': reservas})


from django.db.models import Prefetch

@login_required
def ver_todas_reservas(request):
    """Vista para que el administrador pueda gestionar todas las reservas."""
    # Marcar la notificación como leída si `notificacion_id` está presente
    notificacion_id = request.GET.get('notificacion_id')
    if notificacion_id:
        try:
            notificacion = Notification.objects.get(id=notificacion_id, user=request.user)
            notificacion.is_read = True
            notificacion.save()
        except Notification.DoesNotExist:
            pass  # Si no existe la notificación, continuar sin errores

    # Prefetch para obtener el precio relacionado con ProductoTalla
    reservas = Reserva.objects.select_related('ci', 'id_pro', 'talla').prefetch_related(
        Prefetch(
            'id_pro__producto_tallas',
            queryset=ProductoTalla.objects.select_related('talla').all(),
            to_attr='tallas_disponibles'
        )
    )

    # Agregar el precio al objeto reserva
    for reserva in reservas:
        try:
            producto_talla = next(
                (pt for pt in reserva.id_pro.tallas_disponibles if pt.talla == reserva.talla),
                None
            )
            reserva.precio_talla = producto_talla.precio if producto_talla else None
            reserva.total_reserva = (reserva.precio_talla * reserva.cantidad_reservada) if reserva.precio_talla else None
        except AttributeError:
            reserva.precio_talla = None
            reserva.total_reserva = None

    if request.method == 'POST':
        reserva_id = request.POST.get('reserva_id')
        accion = request.POST.get('accion')

        # Obtener la reserva correspondiente
        reserva = get_object_or_404(Reserva, id_reserva=reserva_id)

        try:
            producto_talla = ProductoTalla.objects.get(producto=reserva.id_pro, talla=reserva.talla)
        except ProductoTalla.DoesNotExist:
            messages.error(request, "El producto o talla de la reserva no existe.", extra_tags="reservas_admin error")
            return redirect('ver_todas_reservas')

        if accion == 'confirmar':
            if reserva.estado_reserva != "Confirmada":
                reserva.estado_reserva = "Confirmada"
                reserva.save()
                Notification.objects.create(
                    user=reserva.ci,
                    message=f"Tu reserva para {reserva.id_pro.nombre_pro} ha sido confirmada.",
                    link="/citas/reservascliente/"
                )
                messages.success(request, f"Reserva {reserva_id} confirmada exitosamente.", extra_tags="reservas_admin success")
            else:
                messages.info(request, f"La reserva {reserva_id} ya estaba confirmada.", extra_tags="reservas_admin info")

        elif accion == 'rechazar':
            if reserva.estado_reserva != "Rechazada":
                producto_talla.cantidad_disponible += reserva.cantidad_reservada
                producto_talla.save()
                producto_talla.sincronizar_stock_con_saleor()
                reserva.estado_reserva = "Rechazada"
                reserva.save()
                Notification.objects.create(
                    user=reserva.ci,
                    message=f"Tu reserva para {reserva.id_pro.nombre_pro} ha sido rechazada.",
                    link="/citas/reservascliente/"
                )
                messages.success(request, f"Reserva {reserva_id} rechazada y unidades devueltas al inventario.", extra_tags="reservas_admin success")
            else:
                messages.info(request, f"La reserva {reserva_id} ya estaba rechazada.", extra_tags="reservas_admin info")

        return redirect('ver_todas_reservas')

    return render(request, 'citas/ver_todas_reservas.html', {'reservas': reservas})

@login_required
def ver_reservas_hoy(request):
    """Vista para mostrar las reservas confirmadas del día actual."""
    fecha_actual = date.today()  # Obtener la fecha actual del sistema
    reservas = Reserva.objects.filter(estado_reserva="Confirmada", date_reserva=fecha_actual)

    # Agregar el precio unitario y el total para cada reserva
    reservas_con_precios = []
    for reserva in reservas:
        try:
            # Obtener el precio unitario desde ProductoTalla
            producto_talla = ProductoTalla.objects.get(producto=reserva.id_pro, talla=reserva.talla)
            precio_unitario = producto_talla.precio
            total = precio_unitario * reserva.cantidad_reservada
        except ProductoTalla.DoesNotExist:
            # Si no se encuentra ProductoTalla, dejar valores nulos
            precio_unitario = None
            total = None

        reservas_con_precios.append({
            'reserva': reserva,
            'precio_unitario': precio_unitario,
            'total': total
        })

    return render(request, 'citas/reservas_hoy.html', {'reservas_con_precios': reservas_con_precios})

@login_required
def calendario_reservas(request):
    """
    Renderiza el calendario para las reservas.
    """
    return render(request, 'citas/calendario_reservas.html')


def verificar_reserva(request):
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora")

    existe = Reserva.objects.filter(date_reserva=fecha, hora_reserva=hora).exists()
    return JsonResponse({'existe': existe})

@login_required
def obtener_reservas(request):
    """
    Devuelve las reservas confirmadas en formato JSON para FullCalendar.
    """
    reservas = Reserva.objects.filter(estado_reserva="Confirmada").values(
        'id_reserva', 'ci__nombre', 'ci__apellido', 'id_pro__nombre_pro', 'date_reserva', 'hora_reserva', 'comentario'
    )
    events = []
    for reserva in reservas:
        events.append({
            'id': reserva['id_reserva'],
            'title': reserva['id_pro__nombre_pro'],  # Solo el nombre del producto en el título
            'client': f"{reserva['ci__nombre']} {reserva['ci__apellido']}",  # Cliente separado
            'start': f"{reserva['date_reserva']}T{reserva['hora_reserva']}",
            'description': reserva['comentario'],
        })
    return JsonResponse(events, safe=False)

@login_required
def verificar_horas_ocupadas(request):
    """
    Devuelve las horas ocupadas para una fecha específica en formato JSON.
    """
    fecha = request.GET.get('fecha')
    if not fecha:
        return JsonResponse({'error': 'Fecha no proporcionada.'}, status=400)
    
    # Filtrar las reservas por fecha
    reservas = Reserva.objects.filter(date_reserva=fecha).values('hora_reserva')
    horas_ocupadas = []

    # Calcular horas ocupadas y sus intervalos de 15 minutos
    for reserva in reservas:
        hora_reserva = reserva['hora_reserva']  # Ya es un objeto datetime.time
        for i in range(0, 15, 15):  # Rango de 15 minutos
            bloque_hora = (datetime.combine(datetime.today(), hora_reserva) + timedelta(minutes=i)).time()
            horas_ocupadas.append(bloque_hora.strftime('%H:%M'))

    return JsonResponse({'horas_ocupadas': list(set(horas_ocupadas))})

@login_required
def marcar_notificacion_leida(request, notificacion_id):
    """
    Marca una notificación como leída.
    """
    try:
        usuario = Usuario.objects.get(email=request.user.username)  # Asegúrate de obtener la instancia del usuario
        notificacion = Notification.objects.get(id=notificacion_id, user=usuario)  # Filtrar por el usuario autenticado
        notificacion.is_read = True
        notificacion.save()
        return JsonResponse({'status': 'success'})
    except Usuario.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Usuario no encontrado.'}, status=404)
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notificación no encontrada.'}, status=404)


@login_required
def obtener_notificaciones(request):
    """
    Obtiene las notificaciones no leídas del usuario autenticado.
    """
    if request.method == 'GET':
        try:
            # Obtener usuario autenticado en el modelo Usuario
            usuario = Usuario.objects.get(email=request.user.username)
        except Usuario.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado.'}, status=404)

        # Filtrar notificaciones no leídas asociadas al usuario
        notificaciones = Notification.objects.filter(user=usuario, is_read=False).order_by('-created_at')
        data = [
            {
                'id': n.id,
                'message': n.message,
                'created_at': n.created_at.strftime('%d %b %Y, %H:%M'),
                'link': n.link,
            }
            for n in notificaciones
        ]
        return JsonResponse({'notificaciones': data, 'count': notificaciones.count()})
    
def eliminar_reserva(request, reserva_id):
    if request.method == "POST":
        reserva = get_object_or_404(Reserva, id_reserva=reserva_id)
        reserva.delete()
        #messages.success(request, "Reserva eliminada exitosamente.")
    return redirect('ver_todas_reservas')  # o el nombre de la vista/lista donde se muestran las reservas

"""@login_required
def obtener_producto_saleor(request, producto_saleor_id):
    
    from catalogo.saleor_api_service import SaleorAPIService
    from catalogo.models import Producto
    
    try:
        # Obtener producto de Django usando el saleor_product_id
        producto_django = Producto.objects.get(saleor_product_id=producto_saleor_id)
        
        # Obtener datos adicionales de Saleor
        saleor_service = SaleorAPIService()
        producto_saleor = saleor_service.obtener_producto_por_id(producto_saleor_id)
        
        if not producto_saleor:
            return JsonResponse({'error': 'Producto no encontrado en Saleor'}, status=404)
        
        # Preparar respuesta
        producto_data = {
            'id': producto_django.id_pro,  # ID de Django para el formulario
            'nombre': producto_django.nombre_pro,
            'descripcion': producto_django.detalle_pro,
            'imagen': producto_django.imagen_pro.url if producto_django.imagen_pro else '/static/images/placeholder.png',
            'tallas': [
                {
                    'talla': talla['talla'],
                    'cantidad': talla['stock'],
                    'precio': talla['precio'],
                    'stock': talla['stock']
                }
                for talla in producto_saleor.get('tallas', [])
            ]
        }
        
        return JsonResponse(producto_data)
        
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado en Django'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
"""

@login_required
def obtener_producto_saleor(request, producto_saleor_id):
    """
    Endpoint para obtener los datos de un producto de Saleor en formato JSON.
    USA EL STOCK REAL DE DJANGO, NO DE SALEOR
    """
    from catalogo.models import Producto
    
    try:
        # Obtener producto de Django usando el saleor_product_id
        producto_django = Producto.objects.get(saleor_product_id=producto_saleor_id)
        
        # 🔥 OBTENER TALLAS DIRECTAMENTE DE DJANGO (fuente de verdad del stock)
        tallas_django = ProductoTalla.objects.filter(
            producto=producto_django,
            cantidad_disponible__gt=0  # Solo tallas con stock
        ).select_related('talla')
        
        # Preparar respuesta con datos de Django
        producto_data = {
            'id': producto_django.id_pro,  # ID de Django para el formulario
            'nombre': producto_django.nombre_pro,
            'descripcion': producto_django.detalle_pro,
            'imagen': producto_django.imagen_pro.url if producto_django.imagen_pro else '/static/images/placeholder.png',
            'tallas': [
                {
                    'talla': pt.talla.talla,
                    'cantidad': pt.cantidad_disponible,  # Stock real de Django
                    'precio': pt.precio,
                    'stock': pt.cantidad_disponible  # Stock real de Django
                }
                for pt in tallas_django
            ]
        }
        
        return JsonResponse(producto_data)
        
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado en Django'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)