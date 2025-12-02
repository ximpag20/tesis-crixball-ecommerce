from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Talla, Rama, Categoria, Favorito
from .forms import ProductoForm, ProductoTalla
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Min, Sum
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import json

#uso de decoradores
@login_required
def Catalogo(request):
    # Importar el servicio de Saleor
    from .saleor_api_service import SaleorAPIService
    
    # Crear instancia del servicio
    saleor_service = SaleorAPIService()
    
    # Obtener productos desde Saleor
    productos_saleor = saleor_service.obtener_productos(first=100)
    
    # Mapear productos de Saleor con productos de Django
    productos_mapeados = []
    for producto_saleor in productos_saleor:
        try:
            # Buscar el producto en Django por su saleor_product_id
            producto_django = Producto.objects.get(saleor_product_id=producto_saleor['id'])
            producto_saleor['id_django'] = producto_django.id_pro
            
            # Usar la imagen de Django/Cloudinary
            if producto_django.imagen_pro:
                producto_saleor['imagen'] = producto_django.imagen_pro.url
            
            # 🔥 NUEVO: Filtrar tallas sin stock
            tallas_con_stock = []
            for talla in producto_saleor['tallas']:
                # Verificar stock en Django (fuente de verdad)
                try:
                    producto_talla = ProductoTalla.objects.get(
                        producto=producto_django,
                        talla__talla=talla['talla']
                    )
                    if producto_talla.cantidad_disponible > 0:
                        # Actualizar con stock real de Django
                        talla['stock'] = producto_talla.cantidad_disponible
                        talla['cantidad'] = producto_talla.cantidad_disponible
                        tallas_con_stock.append(talla)
                except ProductoTalla.DoesNotExist:
                    pass
            
            # 🔥 NUEVO: Solo mostrar producto si tiene tallas con stock
            if not tallas_con_stock:
                print(f"⚠️ Producto sin stock: {producto_saleor['nombre']}")
                continue
            
            producto_saleor['tallas'] = tallas_con_stock
            
            print(f"✅ Mapeado: {producto_saleor['nombre']} -> ID Django: {producto_django.id_pro}")
        except Producto.DoesNotExist:
            print(f"⚠️ Producto de Saleor no encontrado en Django: {producto_saleor['nombre']}")
            continue
        
        productos_mapeados.append(producto_saleor)
        
    print(f"📊 Total productos mapeados: {len(productos_mapeados)}")  # NUEV
    
    # Obtener filtros del frontend
    tallas = Talla.objects.all()
    ramas = Rama.objects.all()
    categorias = Categoria.objects.all()
    
    # Aplicar filtros básicos si es necesario
    talla_filtro = request.GET.get('tallas')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    
    # Filtrar productos según criterios
    productos_filtrados = productos_mapeados
    
    if talla_filtro:
        productos_filtrados = [
            p for p in productos_filtrados 
            if any(t['talla'] == talla_filtro for t in p['tallas'])
        ]
    
    if precio_min:
        precio_min_float = float(precio_min)
        productos_filtrados = [
            p for p in productos_filtrados 
            if p['precio_minimo'] >= precio_min_float
        ]
    
    if precio_max:
        precio_max_float = float(precio_max)
        productos_filtrados = [
            p for p in productos_filtrados 
            if p['precio_minimo'] <= precio_max_float
        ]
    
    return render(request, 'catalogo/index.html', {
        'productos': productos_filtrados,
        'tallas': tallas,
        'ramas': ramas,
        'categorias': categorias,
        'usando_saleor': True,
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


def ver_carrito(request):
    return render(request, "catalogo/ver_carrito.html")


