import os
from dotenv import load_dotenv
import re
import json

from google.cloud import dialogflow_v2 as dialogflow

from google.cloud.dialogflow_v2 import SessionEntityTypesClient
from django.http import JsonResponse
from django.shortcuts import render
from fuzzywuzzy import fuzz
from registro.models import Usuario  # Modelo de usuarios
from catalogo.models import Producto, ProductoTalla  # Modelos de productos y tallas
from chatbot.models import MensajeChat  # Modelo de mensajes del chat
from django.views.decorators.csrf import csrf_exempt

load_dotenv() 

# Establecer las credenciales de la cuenta de servicio para Dialogflow
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def preprocess_message(message):
    """
    Preprocesa el mensaje del usuario eliminando espacios adicionales,
    corrigiendo errores básicos y asegurando uniformidad.
    """
    original_message = message
    message = message.lower()
    message = re.sub(r'\s+', ' ', message).strip()
    message = re.sub(r'(.)\1{2,}', r'\1', message)
    print(f"Mensaje original: '{original_message}', mensaje preprocesado: '{message}'")
    return message

def actualizar_entidades_dinamicas(session_path, productos):
    client = SessionEntityTypesClient()

    # Construye la lista de entidades como diccionarios
    entities = [{"value": p, "synonyms": [p]} for p in productos]
    print(f"[Webhook] Entidades a inyectar: {entities}")

    # Nombre "completo" de la session entity type
    ses_entity_name = f"{session_path}/entityTypes/producto_detalle"

    # Borra cualquier override previo (si existe)
    try:
        client.delete_session_entity_type(name=ses_entity_name)
    except Exception:
        pass

    # Crea el override nuevo usando dict
    client.create_session_entity_type(
        parent=session_path,
        session_entity_type={
            "name": ses_entity_name,
            "entity_override_mode": "ENTITY_OVERRIDE_MODE_OVERRIDE",
            "entities": entities,
        }
    )
    print("[Webhook] Entidades dinámicas actualizadas con éxito.")

def buscar_detalles_producto(producto_nombre):
    """Busca los detalles de un producto en la base de datos, incluyendo tallas y precios."""
    try:
        productos = Producto.objects.filter(nombre_pro__icontains=producto_nombre)
        if productos.exists():
            respuestas = []
            for producto in productos:
                producto_tallas = ProductoTalla.objects.filter(producto=producto)
                if producto_tallas.exists():
                    tallas_info = "<br>".join([
                        f"Talla: {pt.talla.talla}, Precio: {pt.precio}, Cantidad disponible: {pt.cantidad_disponible}"
                        for pt in producto_tallas
                    ])
                    respuestas.append(
                        f"""
                        <div style="line-height: 1.6;">
                            <strong>🛍️ {producto.nombre_pro}</strong><br>
                            📄 {producto.detalle_pro}<br><br>
                            <strong>✏️ Tallas y precios disponibles:</strong><br>
                            {''.join([f'<div style="margin-bottom: 6px;">• Talla: {pt.talla.talla} | Precio: ${pt.precio} | Cantidad: {pt.cantidad_disponible}</div>' for pt in producto_tallas])}
                        </div>
                        """
                    )

                else:
                    respuestas.append(
                        f"El producto '{producto.nombre_pro}' no tiene tallas o precios registrados."
                    )
            return "<br><br>".join(respuestas)
        else:
            productos_disponibles = Producto.objects.values_list('nombre_pro', flat=True)[:5]
            lista_productos = ", ".join(productos_disponibles)
            return (
                f"No se encontró un producto con ese nombre. "
                f"Algunos productos disponibles son: {lista_productos}. "
                "Por favor, verifica e intenta de nuevo."
            )
    except Exception as e:
        print(f"Error buscando detalles del producto: {e}")
        return "Hubo un error buscando los detalles del producto. Por favor, intenta de nuevo más tarde."

def buscar_productos_por_categoria(nombre_categoria):
    from catalogo.models import Categoria, Producto

    try:
        categoria = Categoria.objects.get(nombre_cat__icontains=nombre_categoria)
        productos = Producto.objects.filter(id_rama__id_cat=categoria)

        if productos.exists():
            respuesta = f"<strong>🎯 Productos en la categoría '{categoria.nombre_cat}':</strong><br><ul>"
            for prod in productos:
                respuesta += f"<li>🛍️ <strong>{prod.nombre_pro}</strong> — {prod.detalle_pro}</li>"
            respuesta += "</ul>"
            return respuesta
        else:
            return "No hay productos disponibles en esa categoría por ahora."
    except Categoria.DoesNotExist:
        return f"No encontré la categoría '{nombre_categoria}'. Intenta con otro nombre."

def buscar_productos_por_rama(nombre_rama_usuario):
    from catalogo.models import Rama, Producto

    ramas = Rama.objects.all()
    mejor_rama = None
    mejor_score = 0
    umbral = 70  # puedes ajustar esto

    for rama in ramas:
        score = fuzz.partial_ratio(rama.nombre_rama.lower(), nombre_rama_usuario)
        if score > mejor_score and score >= umbral:
            mejor_rama = rama
            mejor_score = score

    if mejor_rama:
        productos = Producto.objects.filter(id_rama=mejor_rama)
        if productos.exists():
            respuesta = f"<strong>📂 Productos en la rama '{mejor_rama.nombre_rama}':</strong><br><ul>"
            for prod in productos:
                respuesta += f"<li>🧵 <strong>{prod.nombre_pro}</strong>: {prod.detalle_pro}</li>"
            respuesta += "</ul>"
            return respuesta
        else:
            return "No hay productos disponibles en esa rama por ahora."
    else:
        return None  # devolvemos None para que Dialogflow maneje la respuesta


def dialogflow_chat(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").strip()
            if not user_message:
                return JsonResponse({"error": "No se recibió ningún mensaje del usuario."})

            cleaned_message = preprocess_message(user_message)
            # Detectar si el mensaje menciona una categoría existente
            from catalogo.models import Categoria

            categorias = Categoria.objects.values_list('nombre_cat', flat=True)
            # Buscar coincidencia aproximada (fuzzy matching)
            mejor_coincidencia = None
            mejor_score = 0
            umbral = 70  # puedes ajustar el umbral

            for cat in categorias:
                score = fuzz.partial_ratio(cat.lower(), cleaned_message)
                if score > mejor_score and score >= umbral:
                    mejor_coincidencia = cat
                    mejor_score = score

            if mejor_coincidencia:
                bot_response = buscar_productos_por_categoria(mejor_coincidencia)
                return JsonResponse({"response": bot_response})

            # Primero, si no se detecta producto conocido, intenta con ramas (solo si NO hay nombres de productos válidos)
            from catalogo.models import Producto

            # Verificar si el mensaje menciona un producto conocido
            productos = Producto.objects.all()
            encontrado = False
            for p in productos:
                if fuzz.partial_ratio(p.nombre_pro.lower(), cleaned_message) >= 85:
                    encontrado = True
                    break

            # Si no hay match con producto, intentamos con rama
            if not encontrado:
                rama_resultado = buscar_productos_por_rama(cleaned_message)
                if rama_resultado:
                    return JsonResponse({"response": rama_resultado})


            # Configuración de Dialogflow
            project_id = "nth-segment-442814-d7"
            session_id = request.session.session_key or "12345"
            language_code = "es"
            session_client = dialogflow.SessionsClient()
            session = session_client.session_path(project_id, session_id)

            # Obtener lista de productos (para entidad dinámica)
            productos = Producto.objects.values_list('nombre_pro', flat=True)
            actualizar_entidades_dinamicas(session, productos)

                # ——————————————————————————————
            #  Filtro typo “horari” → reenviar a HorariosAtencion en Dialogflow
            if re.search(r'horari', cleaned_message):
                # texto corregido para forzar el intent HorariosAtencion
                corrected_input = "horario de atención"
                text_input  = dialogflow.TextInput(
                    text=corrected_input,
                    language_code=language_code
                )
                query_input = dialogflow.QueryInput(text=text_input)
                df_response = session_client.detect_intent(
                    session=session,
                    query_input=query_input
                )
                return JsonResponse({"response": df_response.query_result.fulfillment_text})
            # ——————————————————————————————


            # Llamar a detect_intent
            text_input = dialogflow.TextInput(text=cleaned_message, language_code=language_code)
            query_input = dialogflow.QueryInput(text=text_input)
            response = session_client.detect_intent(session=session, query_input=query_input)

            # Extraer datos
            intent_name = response.query_result.intent.display_name
            bot_response = response.query_result.fulfillment_text
            parameters = dict(response.query_result.parameters)

            print(f"Intent detectado: {intent_name}")
            print(f"Respuesta de Dialogflow: {bot_response}")
            print(f"Parámetros: {parameters}")

            # Lógica para cada intent
            if intent_name == "ConsultaProductos":
                # Listar productos y guardar en sesión
                todos_productos = Producto.objects.all()
                if todos_productos.exists():
                    lista_nombres = [p.nombre_pro for p in todos_productos]

                    # Guardar la lista en sesión
                    request.session["lista_productos"] = lista_nombres
                    # Forzamos guardado por si tu entorno lo requiere
                    request.session.modified = True

                    product_list_html = "<ul style='padding-left: 18px;'>"
                    for i, p in enumerate(todos_productos, start=1):
                        product_list_html += f"<li><strong>{i}.</strong> {p.nombre_pro}</li>"
                    product_list_html += "</ul>"

                    bot_response = (
                        "📦 <strong>Estos son los productos disponibles:</strong>"
                        f"{product_list_html}"
                        "<br>🛍️ Si te interesa alguno, dime el número del producto para más detalles."
                    )

                else:
                    bot_response = "Actualmente no tenemos productos disponibles en nuestro catálogo."

            elif intent_name == "SeleccionProducto":
                # Aquí recibimos el número (param @sys.number -> 'numero')
                numero = parameters.get("numero", 0)
                try:
                    numero = int(numero)
                except:
                    numero = 0

                # Verificamos el contenido de la sesión
                lista_nombres = request.session.get("lista_productos", [])
                print(f"[DEBUG] lista_productos recuperada: {lista_nombres}")  # Depuración

                if not lista_nombres:
                    bot_response = (
                        "No encuentro la lista de productos en la sesión. "
                        "Puede que la sesión haya expirado. "
                        "Por favor, vuelve a consultar la lista de productos."
                    )
                else:
                    if numero < 1 or numero > len(lista_nombres):
                        bot_response = (
                            "El número que has indicado no es válido. "
                            "Por favor, elige uno de la lista mostrada."
                        )
                    else:
                        producto_seleccionado = lista_nombres[numero - 1]
                        bot_response = buscar_detalles_producto(producto_seleccionado)

            elif intent_name == "DetallesProducto":
                print("🔍 Intent: DetallesProducto")

                # Obtener el texto original enviado por el usuario
                mensaje_usuario = cleaned_message
                print("📝 Mensaje original:", mensaje_usuario)

                # Lista de nombres de productos
                productos = Producto.objects.values_list('nombre_pro', flat=True)
                
                mejor_producto = None
                mejor_score = 0
                umbral = 70  # Puedes ajustar el umbral

                for nombre_producto in productos:
                    score = fuzz.partial_ratio(nombre_producto.lower(), mensaje_usuario)
                    if score > mejor_score and score >= umbral:
                        mejor_producto = nombre_producto
                        mejor_score = score

                if mejor_producto:
                    print("🎯 Producto coincidente:", mejor_producto)
                    bot_response = buscar_detalles_producto(mejor_producto)
                else:
                    bot_response = (
                        "No entendí el nombre del producto. "
                        "Por favor, menciona algo como “Dame detalles de Camiseta de Ecuador”."
                    )



            elif intent_name == "ConsultaBD":
                # Ejemplo: buscar usuarios
                try:
                    if "usuarios registrados" in cleaned_message:
                        usuarios = Usuario.objects.all()
                    else:
                        usuarios = Usuario.objects.filter(nombre__icontains=cleaned_message)

                    if usuarios.exists():
                        formatted_response = "<ul>" + "".join(
                            f"<li><strong>{u.nombre} {u.apellido}</strong>: {u.email}</li>"
                            for u in usuarios
                        ) + "</ul>"
                        return JsonResponse({"response": formatted_response})
                    else:
                        bot_response = "No se encontraron usuarios con ese nombre."
                except Exception as e:
                    print(f"Error consultando usuarios: {e}")
                    bot_response = (
                        "Lo siento, hubo un problema al consultar los usuarios. Inténtalo más tarde."
                    )
            # Guardar mensajes en el historial
            if request.user.is_authenticated:
                try:
                    usuario = Usuario.objects.get(email=request.user.username)
                    MensajeChat.objects.create(usuario=usuario, emisor="usuario", contenido=user_message)
                    MensajeChat.objects.create(usuario=usuario, emisor="bot", contenido=bot_response)
                except Usuario.DoesNotExist:
                    print("⚠️ Usuario no encontrado para guardar historial.")


            # Imprimir y retornar la respuesta
            print(f"Bot response: {bot_response}")
            return JsonResponse({"response": bot_response})

        except Exception as e:
            print(f"Error en la interacción con Dialogflow: {e}")
            return JsonResponse({"error": f"Error interno: {str(e)}"})

    # Si no es POST
    return JsonResponse({"error": "Método de solicitud inválido."}, status=400)

@csrf_exempt
def obtener_historial_chat(request):
    if request.method == "GET" and request.user.is_authenticated:
        try:
            usuario = Usuario.objects.get(email=request.user.username)
            mensajes = MensajeChat.objects.filter(usuario=usuario).order_by("timestamp")
            data = [
                {"rol": "user" if m.emisor == "usuario" else "bot", "contenido": m.contenido}
                for m in mensajes
            ]
            return JsonResponse({"mensajes": data})
        except Usuario.DoesNotExist:
            return JsonResponse({"error": "Usuario no encontrado"}, status=404)
    return JsonResponse({"error": "Método no permitido"}, status=405)

def Chatbot(request):
    mensajes = []
    if request.user.is_authenticated:
        try:
            usuario = Usuario.objects.get(email=request.user.username)
            mensajes = MensajeChat.objects.filter(usuario=usuario).order_by("timestamp")
        except Usuario.DoesNotExist:
            pass

    return render(request, 'chatbot/index.html', {"mensajes": mensajes})



