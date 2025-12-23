import requests
from typing import List, Dict, Optional
from .saleor_auth_service import SaleorAuthService  # 🔥 NUEVO

class SaleorAPIService:
    """
    Servicio para consumir productos desde Saleor y mostrarlos en el frontend
    """
    
    def __init__(self, user_token=None, refresh_token=None, request=None):
        self.api_url = "http://localhost:8001/graphql/"
        self.channel = "default-channel"
        self.auth_service = SaleorAuthService()  # 🔥 NUEVO
        self.user_token = user_token  # 🔥 NUEVO: Token del usuario autenticado
        self.refresh_token = refresh_token
        self.request = request  # 🔥 NUEVO: Objeto request de Django
    
    def _ejecutar_query(self, query: str, variables: dict = None) -> Optional[dict]:
        """Ejecuta una query GraphQL en Saleor"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        token = self.auth_service.obtener_token_valido()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"  # 🔥 NUEVO
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,  # 🔥 CAMBIO AQUÍ
                timeout=10
            )

            # 🔥 Si el token de usuario expiró (401), intentar refresh
            if response.status_code == 401 and self.user_token and self.refresh_token:
                print(f"⚠️ Token de usuario expirado, intentando refresh...")
                
                # Refrescar token
                from .saleor_user_service import SaleorUserService
                user_service = SaleorUserService()
                resultado = user_service.refrescar_token_usuario(self.refresh_token)
                
                if resultado and resultado.get('token'):
                    # Actualizar token en la instancia
                    self.user_token = resultado['token']
                    
                    # 🔥 Actualizar token en la sesión si tenemos acceso al request
                    if self.request:
                        self.request.session['saleor_token'] = resultado['token']
                        self.request.session.modified = True
                        print(f"✅ Token refrescado y guardado en sesión")
                    
                    # Reintentar la query con el nuevo token
                    headers["Authorization"] = f"Bearer {self.user_token}"
                    response = requests.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                else:
                    print(f"❌ No se pudo refrescar el token de usuario")
                    # Fallback: usar token de staff
                    token = self.auth_service.obtener_token_valido()
                    headers["Authorization"] = f"Bearer {token}"
                    response = requests.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
            
            if response.status_code == 200:
                data = response.json()

                    # 🔥 MOSTRAR ERRORES GRAPHQL (CLAVE)
                if "errors" in data:
                    print("❌ GraphQL errors:")
                    for err in data["errors"]:
                        print(err)
                    return None
                if 'data' in data:
                    return data['data']
            
            return None
            
        except Exception as e:
            print(f"❌ Error ejecutando query: {e}")
            return None
    
    def obtener_productos(self, first: int = 100) -> List[Dict]:
        """
        Obtiene todos los productos publicados en Saleor
        
        Returns:
            Lista de productos con sus variantes, precios e imágenes
        """
        query = """
            query GetProducts($channel: String!, $first: Int!) {
                products(first: $first, channel: $channel) {
                    edges {
                        node {
                            id
                            name
                            description
                            thumbnail {
                                url
                            }
                            category {
                                name
                            }
                            variants {
                                id
                                name
                                sku
                                quantityAvailable
                                pricing {
                                    price {
                                        gross {
                                            amount
                                            currency
                                        }
                                    }
                                }
                                attributes {
                                    attribute {
                                        name
                                        slug
                                    }
                                    values {
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        
        variables = {
            "channel": self.channel,
            "first": first
        }
        
        data = self._ejecutar_query(query, variables)
        
        if not data or not data.get('products'):
            return []
        
        # Procesar los productos
        productos_procesados = []
        
        for edge in data['products']['edges']:
            node = edge['node']
            
            # Obtener el precio mínimo de las variantes
            precios = []
            tallas_disponibles = []
            stock_total = 0
            
            for variante in node.get('variants', []):
                if variante.get('pricing') and variante['pricing'].get('price'):
                    precio = variante['pricing']['price']['gross']['amount']
                    precios.append(float(precio))
                
                # Obtener talla
                for attr in variante.get('attributes', []):
                    if attr['attribute']['slug'] == 'talla':
                        talla = attr['values'][0]['name'] if attr['values'] else ''
                        if talla:
                            tallas_disponibles.append({
                                'talla': talla,
                                'precio': float(precio) if precio else 0,
                                'stock': variante.get('quantityAvailable', 0),
                                'variant_id': variante.get('id')
                            })
                
                stock_total += variante.get('quantityAvailable', 0)
            
            # Solo agregar productos con stock
            if stock_total > 0:
                producto = {
                    'id': node['id'],
                    'nombre': node['name'],
                    'descripcion': self._extraer_texto_descripcion(node.get('description', '')),
                    'imagen': node['thumbnail']['url'] if node.get('thumbnail') else None,
                    'categoria': node['category']['name'] if node.get('category') else 'Sin categoría',
                    'precio_minimo': min(precios) if precios else 0,
                    'stock_total': stock_total,
                    'tallas': tallas_disponibles,
                    'variantes': node.get('variants', [])
                }
                
                productos_procesados.append(producto)
        
        return productos_procesados
    
    def obtener_producto_por_id(self, producto_id: str) -> Optional[Dict]:
        """
        Obtiene un producto específico por su ID de Saleor
        
        Args:
            producto_id: ID del producto en Saleor
            
        Returns:
            Diccionario con los datos del producto o None
        """
        query = """
            query GetProduct($id: ID!, $channel: String!) {
                product(id: $id, channel: $channel) {
                    id
                    name
                    description
                    thumbnail {
                        url
                    }
                    media {
                        url
                    }
                    category {
                        name
                    }
                    variants {
                        id
                        name
                        sku
                        quantityAvailable
                        pricing {
                            price {
                                gross {
                                    amount
                                    currency
                                }
                            }
                        }
                        attributes {
                            attribute {
                                name
                                slug
                            }
                            values {
                                name
                            }
                        }
                    }
                }
            }
        """
        
        variables = {
            "id": producto_id,
            "channel": self.channel
        }
        
        data = self._ejecutar_query(query, variables)
        
        if not data or not data.get('product'):
            return None
        
        node = data['product']
        
        # Procesar tallas
        tallas_disponibles = []
        for variante in node.get('variants', []):
            precio = 0
            if variante.get('pricing') and variante['pricing'].get('price'):
                precio = float(variante['pricing']['price']['gross']['amount'])
            
            for attr in variante.get('attributes', []):
                if attr['attribute']['slug'] == 'talla':
                    talla = attr['values'][0]['name'] if attr['values'] else ''
                    if talla and variante.get('quantityAvailable', 0) > 0:
                        tallas_disponibles.append({
                            'talla': talla,
                            'precio': precio,
                            'stock': variante.get('quantityAvailable', 0),
                            'variante_id': variante['id']
                        })
        
        return {
            'id': node['id'],
            'nombre': node['name'],
            'descripcion': self._extraer_texto_descripcion(node.get('description', '')),
            'imagen': node['thumbnail']['url'] if node.get('thumbnail') else None,
            'imagenes': [img['url'] for img in node.get('media', [])],
            'categoria': node['category']['name'] if node.get('category') else 'Sin categoría',
            'tallas': tallas_disponibles
        }
    def _extraer_texto_descripcion(self, description):
        """Extrae el texto plano de la descripción en formato JSON de Saleor"""
        if not description:
            return 'Sin descripción'
        
        try:
            import json
            # Si ya es un dict, úsalo directamente; si es string, conviértelo
            desc_data = json.loads(description) if isinstance(description, str) else description
            
            # Extraer texto de los blocks
            if isinstance(desc_data, dict) and 'blocks' in desc_data:
                textos = []
                for block in desc_data['blocks']:
                    if 'data' in block and 'text' in block['data']:
                        textos.append(block['data']['text'])
                
                return ' '.join(textos) if textos else 'Sin descripción'
            
            return str(desc_data)
        except:
            return 'Sin descripción'

    def actualizar_stock_variante(self, variante_id: str, nueva_cantidad: int, warehouse_id: str) -> bool:
        """
        Actualiza el stock de una variante en Saleor
        
        Args:
            variante_id: ID de la variante en Saleor (ej: "UHJvZHVjdFZhcmlhbnQ6MQ==")
            nueva_cantidad: Nueva cantidad de stock
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        mutation = """
            mutation UpdateStock($variantId: ID!, $quantity: Int!, $warehouse: ID!) {
                productVariantStocksUpdate(
                    variantId: $variantId
                    stocks: [{warehouse: $warehouse, quantity: $quantity}]
                ) {
                    productVariant {
                        id
                        quantityAvailable
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        # ID del warehouse por defecto de Saleor
        # Ajusta esto según tu configuración        
        variables = {
            "variantId": variante_id,
            "quantity": nueva_cantidad,
            "warehouse": warehouse_id
        }

        token = self.auth_service.obtener_token_valido()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": mutation, "variables": variables},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']['productVariantStocksUpdate']:
                    errors = data['data']['productVariantStocksUpdate'].get('errors', [])
                    if not errors:
                        print(f"✅ Stock actualizado en Saleor: Variante {variante_id} -> {nueva_cantidad}")
                        return True
                    else:
                        print(f"❌ Error actualizando stock: {errors}")
                        return False
            
            print(f"❌ Error HTTP {response.status_code}")
            return False
            
        except Exception as e:
            print(f"❌ Error actualizando stock en Saleor: {e}")
            return False


    # ============================================================
    #  CHECKOUT / CARRITO DE SALEOR
    # ============================================================

    def crear_checkout(self, email: str) -> Optional[dict]:
        """
        Crea un checkout vacío en Saleor (equivale a crear carrito).

        Devuelve:
            {
                "checkout": { "id": ..., "token": ... },
                "errors": [...]
            }
        """
        query = """
        mutation CreateCheckout($email: String!) {
          checkoutCreate(
            input: {
              email: $email,
              lines: []
            }
          ) {
            checkout {
              id
              token
            }
            errors {
              field
              message
            }
          }
        }
        """
        variables = {"email": email}

        data = self._ejecutar_query(query, variables)
        if not data:
            return None

        return data.get("checkoutCreate")

    def agregar_linea_checkout(self, checkout_token: str, variant_id: str, quantity: int = 1) -> Optional[dict]:
        """
        Agrega una línea (producto variante) al checkout de Saleor.

        Args:
            checkout_token: token del checkout (guardado en sesión)
            variant_id: ID de la variante de Saleor (no el producto)
            quantity: cantidad a agregar

        Devuelve estructura con checkout y posibles errores.
        """
        query = """
        mutation AddLineToCheckout($token: UUID!, $variantId: ID!, $quantity: Int!) {
          checkoutLinesAdd(
            token: $token,
            lines: [
              {
                quantity: $quantity,
                variantId: $variantId
              }
            ]
          ) {
            checkout {
              id
              token
              totalPrice {
                gross {
                  amount
                  currency
                }
              }
              lines {
                id
                quantity
                totalPrice {
                  gross {
                    amount
                    currency
                  }
                }
                variant {
                  id
                  name
                  product {
                    name
                    thumbnail {
                      url
                    }
                  }
                }
              }
            }
            errors {
              field
              message
            }
          }
        }
        """
        variables = {
            "token": checkout_token,
            "variantId": variant_id,
            "quantity": quantity,
        }

        data = self._ejecutar_query(query, variables)
        if not data:
            return None

        return data.get("checkoutLinesAdd")

    def obtener_checkout(self, checkout_token: str) -> Optional[dict]:
        """
        Obtiene la información completa del checkout (carrito) por su token.
        """
        query = """
        query GetCheckout($token: UUID!) {
          checkout(token: $token) {
            id
            token
            email
            totalPrice {
              gross {
                amount
                currency
              }
            }
            lines {
              id
              quantity
              totalPrice {
                gross {
                  amount
                  currency
                }
              }
              variant {
                id
                name
                quantityAvailable
                pricing {
                    price {
                        gross {
                        amount
                        currency
                        }
                    }
                } 
                product {
                  id
                  name
                  thumbnail {
                    url
                  }
                  media{
                    url
                  }
                }
              }
            }
          }
        }
        """
        variables = {"token": checkout_token}

        data = self._ejecutar_query(query, variables)
        if not data:
            return None

        return data.get("checkout")

    def eliminar_linea_checkout(self, checkout_token: str, line_id: str):
        query = """
        mutation DeleteLines($token: UUID!, $linesIds: [ID!]!) {
        checkoutLinesDelete(
            token: $token,
            linesIds: $linesIds
        ) {
            checkout {
            id
            token
            totalPrice {
                gross {
                amount
                currency
                }
            }
            lines {
                id
                quantity
            }
            }
            errors {
            field
            message
            }
        }
        }
        """
        variables = {
            "token": checkout_token,
            "linesIds": [line_id]  # ← NOMBRE CORRECTO
        }

        return self._ejecutar_query(query, variables)

    def actualizar_cantidad_linea(self, checkout_id, line_id, quantity):
        query = """
        mutation UpdateLine($checkoutId: ID!, $lines: [CheckoutLineUpdateInput!]!) {
        checkoutLinesUpdate(checkoutId: $checkoutId, lines: $lines) {
            checkout {
            id
            totalPrice { gross { amount } }
            lines {
                id
                quantity
                totalPrice { gross { amount } }
            }
            }
            errors { field message }
        }
        }
        """

        variables = {
            "checkoutId": checkout_id,
            "lines": [
                {"lineId": line_id, "quantity": quantity}
            ]
        }

        # ❌ ERROR → self._execute
        # ✔ FIX:
        response = self._ejecutar_query(query, variables)

        return response.get("checkoutLinesUpdate", None)
    
    def forzar_stock(self, variant_id, quantity, warehouse_id):
        mutation = """
        mutation UpdateStock($variantId: ID!, $warehouseId: ID!, $quantity: Int!) {
        productVariantStocksUpdate(
            variantId: $variantId,
            stocks: [{ warehouse: $warehouseId, quantity: $quantity }]
        ) {
            errors { field message code }
        }
        }
        """
        variables = {
            "variantId": variant_id,
            "warehouseId": warehouse_id,
            "quantity": quantity,
        }

        return self._ejecutar_query(mutation, variables)

    def habilitar_variante_en_canal(self, variant_id, channel_slug):
        mutation = """
        mutation EnableVariantInChannel($id: ID!, $channelSlug: String!) {
        productVariantChannelListingUpdate(
            id: $id,
            input: {
            channelListings: [{
                channelSlug: $channelSlug,
                isPublished: true,
                availableForPurchaseAt: "2020-01-01T00:00:00Z"
            }]
            }
        ) {
            errors { field message code }
        }
        }
        """
        variables = {
            "id": variant_id,
            "channelSlug": channel_slug
        }

        return self._ejecutar_query(mutation, variables)

    def debug_shipping_zones(self):
        query = """
        query {
        shippingZones(first: 50) {
            edges {
            node {
                id
                name
                countries {
                code
                country
                }
                warehouses {
                edges {
                    node { id name }
                }
                }
            }
            }
        }
        }
        """
        data = self._ejecutar_query(query)
        if not data:
            return None
        return data.get("shippingZones")

    def debug_warehouses(self):
        query = """
        query {
        warehouses(first: 10) {
            edges {
            node {
                id
                name
            }
            }
        }
        }
        """
        return self._ejecutar_query(query)

    def obtener_lineas_orden(self, order_id):
        query = """
        query OrderLines($id: ID!) {
        order(id: $id) {
            lines {
            id
            quantity
            }
        }
        }
        """
        variables = {"id": order_id}
        data = self._ejecutar_query(query, variables)

        if not data or not data.get("order"):
            return []

        return data["order"]["lines"]
    
    
    def crear_fulfillment(self, order_id, lines):
        mutation = """
        mutation FulfillOrder($orderId: ID!, $lines: [OrderFulfillLineInput!]!) {
        orderFulfill(
            order: $orderId,
            lines: $lines
        ) {
            fulfillment {
            id
            status
            }
            errors {
            field
            message
            }
        }
        }
        """

        variables = {
            "orderId": order_id,
            "lines": lines
        }

        data = self._ejecutar_query(mutation, variables)

        if not data:
            return False

        errors = data["orderFulfill"].get("errors", [])
        if errors:
            print("❌ Error en fulfillment:", errors)
            return False

        print("🚚 Fulfillment creado correctamente")
        return True

