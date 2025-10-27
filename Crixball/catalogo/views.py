from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Talla, Rama, Categoria, Favorito
from .forms import ProductoForm, ProductoTalla
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Min, Sum
from django.views.decorators.csrf import csrf_exempt
import json

#uso de decoradores
@login_required
def Catalogo(request):
    productos = Producto.objects.annotate(
        precio_minimo=Min('producto_tallas__precio'),
        total_stock=Sum('producto_tallas__cantidad_disponible')
    ).filter(total_stock__gt=0)

    tallas = Talla.objects.all()
    ramas = Rama.objects.all()
    categorias = Categoria.objects.all()

    # Aplicar filtros
    talla_id = request.GET.get('tallas')
    rama_id = request.GET.get('ramas')
    categoria_id = request.GET.get('categorias')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    favoritos = request.GET.get('favoritos')

    if talla_id:
        productos = productos.filter(producto_tallas__talla__id_talla=talla_id)
    if rama_id:
        productos = productos.filter(id_rama=rama_id)
    if categoria_id:
        productos = productos.filter(id_rama__id_cat=categoria_id)
    if precio_min:
        productos = productos.filter(producto_tallas__precio__gte=precio_min)
    if precio_max:
        productos = productos.filter(producto_tallas__precio__lte=precio_max)
    if favoritos:
        productos = productos.filter(favoritos__usuario=request.user)  # Lógica para favoritos

    # Agregar estado de favorito a cada producto
    favoritos_ids = Favorito.objects.filter(usuario=request.user).values_list('producto_id', flat=True)
    for producto in productos:
        producto.esfavorito = producto.id_pro in favoritos_ids

    return render(request, 'catalogo/index.html', {
        'productos': productos,
        'tallas': tallas,
        'ramas': ramas,
        'categorias': categorias,
    })


@login_required
def administrar_productos(request):
    success_message = None  # Mensaje de éxito
    error_message = None  # Mensaje de error

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)  # No guarda todavía el producto, solo crea la instancia
            if 'imagen_pro' in request.FILES:  # Verifica si la imagen está presente
                producto.imagen_pro = request.FILES['imagen_pro']
            producto.save()  # Guarda el producto

            form.save_m2m()  # Guarda la relación ManyToMany (tallas)

            # Procesar tallas dinámicas y guardar las cantidades por talla
            tallas = Talla.objects.all()  # Obtiene todas las tallas

            for talla in tallas:
                precio_field = f'precio_{talla.talla}'  # Campo dinámico del precio
                cantidad_field = f'cantidad_{talla.talla}'  # Campo dinámico de la cantidad

                # Extraer datos del POST
                precio = request.POST.get(precio_field, None)
                cantidad = request.POST.get(cantidad_field, None)

                # Verificar que los valores no sean nulos y crear la relación ProductoTalla
                if precio is not None and cantidad is not None:
                    ProductoTalla.objects.create(
                        producto=producto,
                        talla=talla,
                        precio=float(precio),
                        cantidad_disponible=int(cantidad),
                    )

            success_message = 'Producto guardado exitosamente.'
        else:
            error_message = 'Hubo un error en el formulario. Por favor, revisa los datos ingresados.'
            print(form.errors)  # Agrega esta línea para mostrar los errores en la consola
    else:
        form = ProductoForm()

    productos = Producto.objects.all()
    return render(request, 'catalogo/administrar_productos.html', {
        'form': form,
        'productos': productos,
        'success_message': success_message,
        'error_message': error_message,
    })

def DetallesProducto(request, producto_id):
    print("DetallesProducto - Producto ID recibido:", producto_id) 
    producto = get_object_or_404(Producto, id_pro=producto_id)
    tallas = producto.producto_tallas.filter(cantidad_disponible__gt=0)  # Solo tallas con stock
    data = {
        "id": producto.id_pro,  # Agrega el ID al JSON
        "nombre": producto.nombre_pro,
        "descripcion": producto.detalle_pro,
        "imagen": producto.imagen_pro.url if producto.imagen_pro else '',
        "tallas": [
            {
                "talla": pt.talla.talla,
                "cantidad": pt.cantidad_disponible,
                "precio": pt.precio
            }
            for pt in tallas
        ]
    }
    return JsonResponse(data)

@login_required
def toggle_favorito(request, producto_id):
    producto = get_object_or_404(Producto, id_pro=producto_id)
    favorito, created = Favorito.objects.get_or_create(usuario=request.user, producto=producto)

    if not created:
        favorito.delete()
        return JsonResponse({'favorito': False})

    return JsonResponse({'favorito': True})

@csrf_exempt
def actualizar_producto(request, id_pro):
    if request.method == 'POST':
        data = json.loads(request.body)
        campo = data.get('campo')
        valor = data.get('valor')

        try:
            producto = Producto.objects.get(id_pro=id_pro)

            if campo == 'nombre':
                producto.nombre_pro = valor
            elif campo == 'detalle':
                producto.detalle_pro = valor
            else:
                return JsonResponse({'error': 'Campo no válido'}, status=400)

            producto.save()
            return JsonResponse({'mensaje': 'Producto actualizado correctamente'})
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)