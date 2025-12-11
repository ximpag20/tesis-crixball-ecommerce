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

from .saleor_user_service import SaleorUserService
from .saleor_api_service import SaleorAPIService
import json

#uso de decoradores
@login_required
def Catalogo(request):
    
    # 🔥 SINCRONIZACIÓN AUTOMÁTICA AL ACCEDER AL CATÁLOGO
    user_token = request.session.get('saleor_token')
    refresh_token = request.session.get('saleor_refresh_token')
    email = request.session.get('correo_usuario')
    if email:
        user_service = SaleorUserService()
        saleor_user_id = user_service.sincronizar_usuario(email)
        
        if saleor_user_id:
            # Guardar el ID de Saleor en sesión para uso posterior
            request.session['saleor_user_id'] = saleor_user_id
        else:
            print(f"⚠️ No se pudo sincronizar usuario: {email}")

    
    # 🔥 Crear instancia con tokens Y request para poder actualizar sesión
    saleor_service = SaleorAPIService(
        user_token=user_token,
        refresh_token=refresh_token,
        request=request  # 🔥 Importante para actualizar sesión
    )
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


@login_required
def ver_carrito(request):
    checkout_token = request.session.get("checkout_token")
    carrito = None

    if checkout_token:
        saleor = SaleorAPIService()
        carrito = saleor.obtener_checkout(checkout_token)

        if carrito and "lines" in carrito:
            for line in carrito["lines"]:
                product = line["variant"]["product"]

                # 1) Thumbnail de Saleor (si existe)
                if product.get("thumbnail") and product["thumbnail"].get("url"):
                    line["image"] = product["thumbnail"]["url"]

                # 2) Primera imagen del media (si existe)
                elif product.get("media") and len(product["media"]) > 0:
                    line["image"] = product["media"][0]["url"]

                # 3) Imagen desde Django
                else:
                    try:
                        # Buscar por ID de producto en Saleor
                        saleor_id = line["variant"]["product"]["id"]
                        local = Producto.objects.filter(saleor_product_id=saleor_id).first()
                        if local and local.imagen_pro:
                            line["image"] = local.imagen_pro.url
                        else:
                            line["image"] = "/static/img/no_image.png"
                    except:
                        line["image"] = "/static/img/no_image.png"

    return render(request, "catalogo/ver_carrito.html", {
        "carrito": carrito
    })



@login_required
def carrito_agregar(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    data = json.loads(request.body)

    variant_id = data.get("variant_id")
    quantity = int(data.get("quantity", 1))

    if not variant_id:
        return JsonResponse({"error": "variant_id requerido"}, status=400)

    # 🔥 Crear servicio con tokens del usuario
    user_token = request.session.get('saleor_token')
    refresh_token = request.session.get('saleor_refresh_token')

    saleor = SaleorAPIService(
        user_token=user_token,
        refresh_token=refresh_token,
        request=request
    )

    # Obtener o crear checkout
    checkout_token = request.session.get("checkout_token")
    email = request.session.get('correo_usuario', request.user.email)

    if not checkout_token:
        nuevo_checkout = saleor.crear_checkout(email)
        checkout_token = nuevo_checkout["checkout"]["token"]
        request.session["checkout_token"] = checkout_token

    # Agregar línea a Saleor
    resultado = saleor.agregar_linea_checkout(checkout_token, variant_id, quantity)

    # 🔥🔥🔥 ADJUNTAR IMAGEN DESDE DJANGO AL OBJETO RETORNADO 🔥🔥🔥
    imagen_url = "/static/img/no_image.png"

    # Buscar el producto en Django por variant_id
    try:
        prod = Producto.objects.get(saleor_variant_id=variant_id)
        if prod.imagen_pro:
            imagen_url = prod.imagen_pro.url
    except:
        pass

    # Si Saleor devolvió checkout y líneas, inyectar imagen
    if resultado and resultado.get("checkout") and resultado["checkout"].get("lines"):
        for line in resultado["checkout"]["lines"]:
            line["image"] = imagen_url

    return JsonResponse({
        "status": "ok",
        "checkout": resultado
    })


@login_required
def carrito_eliminar(request, line_id):
    checkout_token = request.session.get("checkout_token")
    if not checkout_token:
        return redirect("ver_carrito")

    saleor = SaleorAPIService()
    saleor.eliminar_linea_checkout(checkout_token, line_id)

    return redirect("ver_carrito")



def carrito_eliminar(request, line_id):
    print("🟠 Entró a carrito_eliminar con LINE_ID =", line_id)

    checkout_token = request.session.get("checkout_token")
    if not checkout_token:
        print("❌ No hay checkout_token en sesión")
        return redirect("ver_carrito")

    saleor = SaleorAPIService()

    # Obtener checkout completo
    checkout = saleor.obtener_checkout(checkout_token)
    print("🟢 Checkout obtenido:", checkout)

    if not checkout:
        print("❌ Saleor NO devolvió checkout")
        return redirect("ver_carrito")

    checkout_id = checkout.get("id")
    print("🔵 Checkout ID real:", checkout_id)

    resultado = saleor.eliminar_linea_checkout(checkout_id, line_id)

    print("🔍 RESPUESTA DE SALEOR AL BORRAR:", resultado)

    resultado = saleor.eliminar_linea_checkout(checkout_token, line_id)
    print("🔍 RESPUESTA DE SALEOR AL BORRAR:", resultado)


    return redirect("ver_carrito")

# catalogo/views.py

@login_required
def checkout_view(request):
    checkout_token = request.session.get("checkout_token")
    carrito = None

    if checkout_token:
        saleor = SaleorAPIService()
        carrito = saleor.obtener_checkout(checkout_token)

    if not carrito:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("catalogo")
    
        # 🔥 AGREGAR IMÁGENES A LAS LÍNEAS DEL CARRITO
    if carrito and "lines" in carrito:
        for line in carrito["lines"]:
            product = line["variant"]["product"]

            # 1) Thumbnail de Saleor (si existe)
            if product.get("thumbnail") and product["thumbnail"].get("url"):
                line["image"] = product["thumbnail"]["url"]

            # 2) Primera imagen del media (si existe)
            elif product.get("media") and len(product["media"]) > 0:
                line["image"] = product["media"][0]["url"]

            # 3) 🔥 Imagen desde Django/Cloudinary (RECOMENDADO)
            else:
                try:
                    # Buscar por ID de producto en Saleor
                    saleor_id = line["variant"]["product"]["id"]
                    local = Producto.objects.filter(saleor_product_id=saleor_id).first()
                    if local and local.imagen_pro:
                        line["image"] = local.imagen_pro.url
                    else:
                        line["image"] = "/static/img/no_image.png"
                except:
                    line["image"] = "/static/img/no_image.png"

    # 🔥 OBTENER DATOS DEL USUARIO
    email_usuario = request.session.get('correo_usuario')
    user_token = request.session.get('saleor_token')
    refresh_token = request.session.get('saleor_refresh_token')
    
    datos_usuario = {
        'email': '',
        'first_name': '',
        'last_name': '',
        'doc_number': '',
        'phone': ''
    }
    
    # 🔥 PASO 1: Intentar obtener datos de Saleor
    if user_token:
        from .saleor_user_service import SaleorUserService
        user_service = SaleorUserService()
        usuario_saleor = user_service.obtener_usuario_actual(user_token)
        
        # 🔥 Si el token expiró, intentar refresh
        if not usuario_saleor and refresh_token:
            print(f"🔄 Token expirado, intentando refresh...")
            resultado_refresh = user_service.refrescar_token_usuario(refresh_token)
            
            if resultado_refresh and resultado_refresh.get('token'):
                # Actualizar token en sesión
                nuevo_token = resultado_refresh['token']
                request.session['saleor_token'] = nuevo_token
                request.session.modified = True
                print(f"✅ Token refrescado exitosamente")
                
                # Reintentar obtener datos con el nuevo token
                usuario_saleor = user_service.obtener_usuario_actual(nuevo_token)
            else:
                print(f"❌ No se pudo refrescar el token")
        
        if usuario_saleor:
            datos_usuario['email'] = usuario_saleor.get('email', '')
            datos_usuario['first_name'] = usuario_saleor.get('firstName', '')
            datos_usuario['last_name'] = usuario_saleor.get('lastName', '')
            print(f"✅ Datos de Saleor obtenidos: {datos_usuario['email']}")
    
    # 🔥 PASO 2: Obtener datos de Django (doc_number, phone)
    # Y TAMBIÉN usar Django como fallback para email, nombre, apellido
    if email_usuario:
        try:
            from registro.models import Usuario
            usuario_django = Usuario.objects.get(email=email_usuario)
            
            # Datos siempre de Django
            datos_usuario['doc_number'] = usuario_django.ci
            datos_usuario['phone'] = usuario_django.tel
            
            # 🔥 FALLBACK: Si no hay datos de Saleor, usar Django
            if not datos_usuario['email']:
                datos_usuario['email'] = usuario_django.email
                datos_usuario['first_name'] = usuario_django.nombre
                datos_usuario['last_name'] = usuario_django.apellido
                print(f"✅ Usando datos de Django como fallback: {usuario_django.email}")
            
            print(f"✅ Datos de Django obtenidos: CI={usuario_django.ci}, Tel={usuario_django.tel}")
        except Usuario.DoesNotExist:
            print(f"❌ Usuario no encontrado en Django: {email_usuario}")
    
    return render(request, "catalogo/checkout.html", {
        "carrito": carrito,
        "datos_usuario": datos_usuario
    })

@login_required
def carrito_actualizar_cantidad(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    data = json.loads(request.body)
    line_id = data.get("line_id")
    quantity = int(data.get("quantity", 1))
    stock_max = int(data.get("stock_max", 99))

    # Validación de stock
    if quantity > stock_max:
        return JsonResponse({
            "status": "error",
            "message": "Has superado el stock disponible."
        })

    checkout_token = request.session.get("checkout_token")
    if not checkout_token:
        return JsonResponse({"error": "No hay checkout activo"}, status=400)

    saleor = SaleorAPIService()
    checkout = saleor.obtener_checkout(checkout_token)

    checkout_id = checkout.get("id")
    result = saleor.actualizar_cantidad_linea(checkout_id, line_id, quantity)

    # result YA ES checkoutLinesUpdate → no busques otra clave
    if not result:
        return JsonResponse({
            "status": "error",
            "message": "Error actualizando cantidad."
        })

    checkout_data = result.get("checkout")  # ← ESTE ES EL CHECKOUT FINAL

    return JsonResponse({
        "status": "ok",
        "checkout": checkout_data
    })


