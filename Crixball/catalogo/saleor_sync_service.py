import requests
import json
from decimal import Decimal
from typing import Dict, List, Optional


class SaleorSyncService:
    """
    Servicio para sincronizar productos de Crixball hacia Saleor.
    Maneja la creación y actualización de productos con sus variantes (tallas).
    """
    
    def __init__(self):
        # Configuración de Saleor
        self.api_url = "http://localhost:8001/graphql/"
        self.channel = "default-channel"
        
        # Token de autenticación (opcional por ahora)
        # Si tienes un token de admin, agrégalo aquí:
        # self.token = "TU_TOKEN_AQUI"
        self.token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IlJGWXhJU0ZhdVR6NjR2TEtZRFUyNWxEbnB4YXBGSUxqSHFUek1DcFpCMmciLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NjM5Nzk4NTcsIm93bmVyIjoic2FsZW9yIiwiaXNzIjoiaHR0cDovL2xvY2FsaG9zdDo4MDAwL2dyYXBocWwvIiwiZXhwIjoxNzYzOTgwMTU3LCJ0b2tlbiI6IlJ5M3ZpYTVQbGlicyIsImVtYWlsIjoicGFndWF5eGltZW5hNEBnbWFpbC5jb20iLCJ0eXBlIjoiYWNjZXNzIiwidXNlcl9pZCI6IlZYTmxjam94IiwiaXNfc3RhZmYiOnRydWV9.Kn4zIUkVaQfBSg3uZcfsmRJJD1VCoHe6DYnB4jsjheD1k-55hjsEsdfYB5R6YUq-24DG__ZdNPNZxXUWjPvvhR8WQl5T_LwpYSI3aXzPCpbmPqsuRu_-d9v4-8iPd45DPJqq-9VlEz7mbLp_qZyTuzHvQWwUv__Enhdld6r37hnK-cKPnivHgYPvKEq5bt6ipOGWW1VKIeDodroXswBtHZfMr_0EyLKJOKOtHMLhYw9Y1L4PLdIXSAxlZynmLAS1P_Wk3PecQrOIBNh-UGVzFRPNIxSqjzeGhojrT6zfWnOnZQz3b57QdETf9JqrFgaZsYMlzCtg95j2BMsihV5usg"
    def _get_headers(self):
        """Genera los headers para las peticiones"""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Si tienes token, lo agregamos
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        return headers
    
    def ejecutar_mutation(self, mutation: str, variables: dict = None) -> Optional[dict]:
        """
        Ejecuta una mutación GraphQL en Saleor
        
        Args:
            mutation: Query de GraphQL a ejecutar
            variables: Variables para la mutación
            
        Returns:
            Datos de respuesta o None si hay error
        """
        payload = {"query": mutation}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verificar si hay errores en la respuesta
                if 'errors' in data:
                    print(f"❌ GraphQL Errors:")
                    for error in data['errors']:
                        print(f"   - {error.get('message', 'Error desconocido')}")
                    return None
                    
                if 'data' in data:
                    return data['data']
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ No se puede conectar con Saleor. ¿Está corriendo en localhost:8001?")
        except Exception as e:
            print(f"❌ Error ejecutando mutación: {e}")
        
        return None
    
    def obtener_o_crear_categoria(self, nombre_categoria: str) -> Optional[str]:
        """
        Obtiene el ID de una categoría existente o la crea si no existe
        
        Args:
            nombre_categoria: Nombre de la categoría
            
        Returns:
            ID de la categoría en Saleor o None si falla
        """
        # Primero intentar obtener la categoría
        query = """
            query GetCategories($name: String!) {
                categories(first: 1, filter: {search: $name}) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """
        
        variables = {"name": nombre_categoria}
        data = self.ejecutar_mutation(query, variables)
        
        if data and data.get('categories', {}).get('edges'):
            categoria_id = data['categories']['edges'][0]['node']['id']
            print(f"✅ Categoría '{nombre_categoria}' encontrada: {categoria_id}")
            return categoria_id
        
        # Si no existe, crear la categoría
        mutation = """
            mutation CreateCategory($input: CategoryInput!) {
                categoryCreate(input: $input) {
                    category {
                        id
                        name
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "input": {
                "name": nombre_categoria,
                "slug": nombre_categoria.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('categoryCreate', {}).get('category'):
            categoria_id = data['categoryCreate']['category']['id']
            print(f"✅ Categoría '{nombre_categoria}' creada: {categoria_id}")
            return categoria_id
        
        print(f"❌ No se pudo crear la categoría '{nombre_categoria}'")
        return None
    
    def sincronizar_producto(self, producto_crixball) -> bool:
        """
        Sincroniza un producto de Crixball a Saleor
        
        Args:
            producto_crixball: Instancia del modelo Producto de Django
            
        Returns:
            True si la sincronización fue exitosa, False en caso contrario
        """
        print(f"\n🔄 Sincronizando producto: {producto_crixball.nombre_pro}")
        
        # 1. Obtener o crear la categoría
        nombre_categoria = producto_crixball.id_rama.id_cat.nombre_cat
        categoria_id = self.obtener_o_crear_categoria(nombre_categoria)
        
        if not categoria_id:
            print(f"❌ No se pudo obtener/crear la categoría para {producto_crixball.nombre_pro}")
            return False
        
        # 2. Verificar si el producto ya existe en Saleor
        producto_saleor_id = self._buscar_producto_por_sku(f"CRIX-{producto_crixball.id_pro}")
        
        if producto_saleor_id:
            print(f"📦 Producto ya existe en Saleor, actualizando...")
            return self._actualizar_producto(producto_crixball, producto_saleor_id, categoria_id)
        else:
            print(f"📦 Producto nuevo, creando en Saleor...")
            return self._crear_producto(producto_crixball, categoria_id)
    
    def _buscar_producto_por_sku(self, sku: str) -> Optional[str]:
        """Busca un producto en Saleor por su SKU"""
        query = """
            query SearchProduct($sku: String!) {
                products(first: 1, filter: {search: $sku}, channel: "default-channel") {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """
        
        variables = {"sku": sku}
        data = self.ejecutar_mutation(query, variables)
        
        if data and data.get('products', {}).get('edges'):
            return data['products']['edges'][0]['node']['id']
        
        return None
    
    def _crear_producto(self, producto_crixball, categoria_id: str) -> bool:
        """Crea un nuevo producto en Saleor con sus variantes"""
        
        # Preparar la descripción en formato JSON para Saleor
        descripcion_json = {
            "blocks": [
                {
                    "type": "paragraph",
                    "data": {
                        "text": producto_crixball.detalle_pro
                    }
                }
            ]
        }
        
        # Mutation para crear el producto
        mutation = """
            mutation CreateProduct($input: ProductCreateInput!) {
                productCreate(input: $input) {
                    product {
                        id
                        name
                        variants {
                            id
                        }
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        # Preparar el input
        product_input = {
            "name": producto_crixball.nombre_pro,
            "slug": f"crix-{producto_crixball.id_pro}-{producto_crixball.nombre_pro.lower().replace(' ', '-')[:50]}",
            "description": json.dumps(descripcion_json),
            "category": categoria_id,
            "productType": self._obtener_product_type_id(),
        }
        
        variables = {"input": product_input}
        data = self.ejecutar_mutation(mutation, variables)
        
        if not data:
            print(f"❌ Error creando producto en Saleor - No se recibió respuesta")
            return False
        
        # Verificar errores específicos de la mutación
        if data.get('productCreate', {}).get('errors'):
            print(f"❌ Errores al crear producto:")
            for error in data['productCreate']['errors']:
                print(f"   Campo: {error.get('field', 'N/A')}")
                print(f"   Mensaje: {error.get('message', 'Error desconocido')}")
            return False
        
        if not data.get('productCreate', {}).get('product'):
            print(f"❌ Error creando producto en Saleor - No se creó el producto")
            return False
        
        producto_saleor = data['productCreate']['product']
        producto_saleor_id = producto_saleor['id']
        print(f"✅ Producto creado en Saleor: {producto_saleor_id}")

        # Guardar el ID de Saleor en el producto de Django
        producto_crixball.saleor_product_id = producto_saleor_id
        producto_crixball.save()
        print(f"   💾 ID de Saleor guardado en Django: {producto_saleor_id}")

        # Publicar el producto en el canal
        self._publicar_producto_en_canal(producto_saleor_id)

        if producto_crixball.imagen_pro:
            self._subir_imagen_producto(producto_saleor_id, producto_crixball.imagen_pro)
        
        # 3. Crear las variantes (tallas)
        return self._crear_variantes(producto_crixball, producto_saleor_id)
    
    def _actualizar_producto(self, producto_crixball, producto_saleor_id: str, categoria_id: str) -> bool:
        """Actualiza un producto existente en Saleor"""
        
        descripcion_json = {
            "blocks": [
                {
                    "type": "paragraph",
                    "data": {
                        "text": producto_crixball.detalle_pro
                    }
                }
            ]
        }
        
        mutation = """
            mutation UpdateProduct($id: ID!, $input: ProductInput!) {
                productUpdate(id: $id, input: $input) {
                    product {
                        id
                        name
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "id": producto_saleor_id,
            "input": {
                "name": producto_crixball.nombre_pro,
                "description": json.dumps(descripcion_json),
                "category": categoria_id,
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('productUpdate', {}).get('product'):
            print(f"✅ Producto actualizado en Saleor")

            if not producto_crixball.saleor_product_id:
                producto_crixball.saleor_product_id = producto_saleor_id
                producto_crixball.save()
                print(f"   💾 ID de Saleor guardado: {producto_saleor_id}")
            # Actualizar variantes
            return self._crear_variantes(producto_crixball, producto_saleor_id)
        
        return False
    
    def _crear_variantes(self, producto_crixball, producto_saleor_id: str) -> bool:
        """Crea o actualiza las variantes (tallas) de un producto"""
        
        # Obtener todas las tallas del producto
        producto_tallas = producto_crixball.producto_tallas.all()
        
        if not producto_tallas:
            print("⚠️  No hay tallas para sincronizar")
            return True
        
        exito_total = True
        
        for pt in producto_tallas:
            # SKU único para cada variante
            sku = f"CRIX-{producto_crixball.id_pro}-{pt.talla.talla}"
            
            # Verificar si la variante ya existe
            variante_id = self._buscar_variante_por_sku(producto_saleor_id, sku)
            
            if variante_id:
                # Actualizar variante existente
                exito = self._actualizar_variante(variante_id, pt, sku)
            else:
                # Crear nueva variante
                exito = self._crear_variante(producto_saleor_id, pt, sku)
            
            if not exito:
                exito_total = False
        
        return exito_total
    
    def _buscar_variante_por_sku(self, producto_id: str, sku: str) -> Optional[str]:
        """Busca una variante específica por SKU"""
        query = """
            query GetProduct($id: ID!) {
                product(id: $id, channel: "default-channel") {
                    variants {
                        id
                        sku
                    }
                }
            }
        """
        
        variables = {"id": producto_id}
        data = self.ejecutar_mutation(query, variables)
        
        # Verificar que data no sea None antes de acceder
        if data is None:
            return None
            
        if data.get('product') and data['product'].get('variants'):
            for variante in data['product']['variants']:
                if variante.get('sku') == sku:
                    return variante['id']
        
        return None
    
    def _crear_variante(self, producto_id: str, producto_talla, sku: str) -> bool:
        """Crea una nueva variante en Saleor"""
        
        # Obtener el atributo Talla
        atributo_talla_id = self._obtener_attribute_id("Talla")
        
        if not atributo_talla_id:
            print(f"  ❌ No se pudo obtener el atributo Talla")
            return False
        
        mutation = """
            mutation CreateVariant($productId: ID!, $input: ProductVariantBulkCreateInput!) { 
                productVariantBulkCreate(product: $productId, variants: [$input]) {
                    productVariants {
                        id
                        name
                        sku
                    }
                    errors {
                        field
                        message
                        code
                    }
                }
            }
        """
        
        variables = {
            "productId": producto_id,
            "input": { 
                "sku": sku,
                "name": f"Talla {producto_talla.talla.talla}",
                "trackInventory": True,
                "attributes": [
                    {
                        "id": atributo_talla_id,
                        "values": [str(producto_talla.talla.talla)]
                    }
                ],
                "stocks": [
                    {
                        "warehouse": self._obtener_warehouse_id(),
                        "quantity": int(producto_talla.cantidad_disponible)
                    }
                ],
                "channelListings": [
                    {
                        "channelId": self._obtener_channel_id(),
                        "price": float(producto_talla.precio),
                        "costPrice": float(producto_talla.precio)
                    }
                ]
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('productVariantBulkCreate', {}).get('productVariants'):
            variantes = data['productVariantBulkCreate']['productVariants']
            if variantes and len(variantes) > 0:
                print(f"  ✅ Variante creada: Talla {producto_talla.talla.talla} (Stock: {producto_talla.cantidad_disponible}, Precio: ${producto_talla.precio})")
                return True
        
        # Mostrar errores si los hay
        if data and data.get('productVariantBulkCreate', {}).get('errors'):
            print(f"  ❌ Error creando variante: Talla {producto_talla.talla.talla}")
            for error in data['productVariantBulkCreate']['errors']:
                print(f"     Campo: {error.get('field', 'N/A')}")
                print(f"     Mensaje: {error.get('message', 'Error desconocido')}")
                print(f"     Código: {error.get('code', 'N/A')}")
        else:
            print(f"  ❌ Error creando variante: Talla {producto_talla.talla.talla} (sin detalles)")
        
        return False
    
    def _actualizar_variante(self, variante_id: str, producto_talla, sku: str) -> bool:
        """Actualiza una variante existente"""
        
        # Actualizar stock
        mutation_stock = """
            mutation UpdateStock($variantId: ID!, $stocks: [StockInput!]!) {
                productVariantStocksUpdate(variantId: $variantId, stocks: $stocks) {
                    productVariant {
                        id
                        name
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables_stock = {
            "variantId": variante_id,
            "stocks": [
                {
                    "warehouse": self._obtener_warehouse_id(),
                    "quantity": int(producto_talla.cantidad_disponible)
                }
            ]
        }
        
        data = self.ejecutar_mutation(mutation_stock, variables_stock)
        
        if data and data.get('productVariantStocksUpdate', {}).get('productVariant'):
            print(f"  ✅ Stock actualizado: Talla {producto_talla.talla.talla}")
            # Actualizar precio
            return self._asignar_precio_variante(variante_id, producto_talla.precio)
        
        return False
    
    def _asignar_precio_variante(self, variante_id: str, precio: Decimal) -> bool:
        """Asigna precio a una variante en el canal default"""
        
        mutation = """
            mutation UpdateChannelListing($id: ID!, $input: [ProductVariantChannelListingAddInput!]!) {
                productVariantChannelListingUpdate(id: $id, input: $input) {
                    variant {
                        id
                        channelListings {
                            price {
                                amount
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
            "id": variante_id,
            "input": [
                {
                    "channelId": self._obtener_channel_id(),
                    "price": float(precio)
                }
            ]
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('productVariantChannelListingUpdate', {}).get('variant'):
            return True
        
        return False
    
    def _obtener_product_type_id(self) -> str:
        """Obtiene el ID del tipo de producto que permite variantes o lo crea"""
        query = """
            query {
                productTypes(first: 20) {
                    edges {
                        node {
                            id
                            name
                            hasVariants
                            variantAttributes {
                                id
                                name
                                slug
                            }
                        }
                    }
                }
            }
        """
        
        data = self.ejecutar_mutation(query)
        
        if data and data.get('productTypes', {}).get('edges'):
            # Buscar un tipo que permita variantes Y tenga el atributo Talla
            for edge in data['productTypes']['edges']:
                node = edge['node']
                if node.get('hasVariants'):
                    # Verificar si tiene el atributo Talla
                    variant_attrs = node.get('variantAttributes', [])
                    for attr in variant_attrs:
                        if attr.get('slug') == 'talla':
                            print(f"   ✅ Usando ProductType: {node['name']} (con variantes y atributo Talla)")
                            return node['id']
            
            # Si hay uno con variantes pero sin Talla, usarlo de todas formas
            for edge in data['productTypes']['edges']:
                if edge['node'].get('hasVariants'):
                    print(f"   ⚠️  Usando ProductType: {edge['node']['name']} (tiene variantes pero falta atributo Talla)")
                    return edge['node']['id']
            
            # Si no hay ninguno con variantes, crear uno nuevo
            print(f"   ⚠️  No hay ProductType con variantes, creando uno nuevo...")
            return self._crear_product_type_con_variantes()
        
        # Si no se encontró nada, crear uno nuevo
        print(f"   ⚠️  No se encontraron ProductTypes, creando uno nuevo...")
        return self._crear_product_type_con_variantes()

    def _obtener_attribute_id(self, nombre_atributo: str) -> Optional[str]:
        """Obtiene el ID del atributo (por ejemplo 'Talla')"""
        query = """
            query {
                attributes(first: 20, filter: {type: PRODUCT_TYPE}) {
                    edges {
                        node {
                            id
                            name
                            slug
                        }
                    }
                }
            }
        """
        
        data = self.ejecutar_mutation(query)
        
        # Si el atributo ya existe
        if data and data.get("attributes") and data["attributes"].get("edges"):
            for edge in data["attributes"]["edges"]:
                if edge["node"]["slug"] == nombre_atributo.lower():
                    return edge["node"]["id"]
        
        # Si no existe, intentar crearlo usando el método auxiliar
        print(f"   ⚠️  Atributo '{nombre_atributo}' no encontrado, intentando crear...")
        return self._obtener_o_crear_atributo_talla()
    
    def _obtener_warehouse_id(self) -> str:
        """Obtiene el ID del warehouse por defecto"""
        query = """
            query {
                warehouses(first: 1) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        """
        
        data = self.ejecutar_mutation(query)
        
        if data and data.get('warehouses', {}).get('edges'):
            warehouse_id = data['warehouses']['edges'][0]['node']['id']
            return warehouse_id
        
        # ID por defecto
        return "V2FyZWhvdXNlOjE="
    
    def _obtener_channel_id(self) -> str:
        """Obtiene el ID del canal por defecto"""
        query = """
            query {
                channels {
                    id
                    slug
                    name
                }
            }
        """
        
        data = self.ejecutar_mutation(query)
        
        if data and data.get('channels'):
            for channel in data['channels']:
                if channel['slug'] == self.channel:
                    return channel['id']
        
        # ID por defecto del canal default-channel
        return "Q2hhbm5lbDox"
    
    def _publicar_producto_en_canal(self, producto_id: str) -> bool:
        """Publica un producto en el canal default"""
        
        mutation = """
            mutation PublishProduct($id: ID!, $input: ProductChannelListingUpdateInput!) {
                productChannelListingUpdate(id: $id, input: $input) {
                    product {
                        id
                        name
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "id": producto_id,
            "input": {
                "updateChannels": [
                    {
                        "channelId": self._obtener_channel_id(),
                        "isPublished": True,
                        "visibleInListings": True,
                        "isAvailableForPurchase": True
                    }
                ]
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('productChannelListingUpdate', {}).get('product'):
            print(f"   ✅ Producto publicado en canal")
            return True
        
        # Mostrar errores si los hay
        if data and data.get('productChannelListingUpdate', {}).get('errors'):
            print(f"   ❌ Error publicando en canal:")
            for error in data['productChannelListingUpdate']['errors']:
                print(f"      Campo: {error.get('field', 'N/A')}")
                print(f"      Mensaje: {error.get('message', 'Error desconocido')}")
        else:
            print(f"   ⚠️  No se pudo publicar en canal")
        
        return False
    
    def _crear_tipo_producto_con_variantes(self):
        mutation = """
            mutation CreateProductType($input: ProductTypeCreateInput!) {
                productTypeCreate(input: $input) {
                    productType {
                        id
                        name
                        hasVariants
                        variantAttributes {
                            name
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
            "input": {
                "name": "Ropa con tallas",
                "slug": "ropa-con-tallas",
                "hasVariants": True,
                "productAttributes": [],
                "variantAttributes": [],
                "isShippingRequired": True,
            }
        }

        data = self.ejecutar_mutation(mutation, variables)
        print(data)

    def _crear_product_type_con_variantes(self) -> str:
        """Crea un ProductType con soporte para variantes y atributo Talla"""
        
        # Primero, obtener o crear el atributo Talla
        atributo_talla_id = self._obtener_o_crear_atributo_talla()
        
        if not atributo_talla_id:
            print("❌ No se pudo crear el atributo Talla")
            return "UHJvZHVjdFR5cGU6MQ=="  # Retornar ID por defecto
        
        mutation = """
            mutation CreateProductType($input: ProductTypeInput!) {
                productTypeUpdate(id: "UHJvZHVjdFR5cGU6MQ==", input: $input) {
                    productType {
                        id
                        name
                        hasVariants
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "input": {
                "hasVariants": True,
                "variantAttributes": [atributo_talla_id]
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('productTypeUpdate', {}).get('productType'):
            product_type_id = data['productTypeUpdate']['productType']['id']
            print(f"   ✅ ProductType actualizado con variantes: {product_type_id}")
            return product_type_id
        
        if data and data.get('productTypeUpdate', {}).get('errors'):
            print("   ❌ Errores al actualizar ProductType:")
            for error in data['productTypeUpdate']['errors']:
                print(f"      {error.get('field')}: {error.get('message')}")
        
        return "UHJvZHVjdFR5cGU6MQ=="

    def _obtener_o_crear_atributo_talla(self) -> Optional[str]:
        """Obtiene o crea el atributo Talla para variantes"""
        
        # Primero intentar obtener el atributo existente
        query = """
            query {
                attributes(first: 20, filter: {type: PRODUCT_TYPE}) {
                    edges {
                        node {
                            id
                            name
                            slug
                            inputType
                        }
                    }
                }
            }
        """
        
        data = self.ejecutar_mutation(query)
        
        if data and data.get('attributes', {}).get('edges'):
            for edge in data['attributes']['edges']:
                if edge['node']['slug'] == 'talla':
                    print(f"   ✅ Atributo Talla encontrado: {edge['node']['id']}")
                    return edge['node']['id']
        
        # Si no existe, crear el atributo
        print("   📝 Creando atributo Talla...")
        
        mutation = """
            mutation CreateAttribute($input: AttributeCreateInput!) {
                attributeCreate(input: $input) {
                    attribute {
                        id
                        name
                        slug
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "input": {
                "name": "Talla",
                "slug": "talla",
                "type": "PRODUCT_TYPE",
                "inputType": "DROPDOWN",
                "valueRequired": False,
                "isVariantOnly": True,
                "values": [
                    {"name": "28"},
                    {"name": "30"},
                    {"name": "32"},
                    {"name": "34"},
                    {"name": "36"},
                    {"name": "38"},
                    {"name": "S"},
                    {"name": "M"},
                    {"name": "L"},
                    {"name": "XL"}
                ]
            }
        }
        
        data = self.ejecutar_mutation(mutation, variables)
        
        if data and data.get('attributeCreate', {}).get('attribute'):
            atributo_id = data['attributeCreate']['attribute']['id']
            print(f"   ✅ Atributo Talla creado: {atributo_id}")
            return atributo_id
        
        if data and data.get('attributeCreate', {}).get('errors'):
            print("   ❌ Errores al crear atributo:")
            for error in data['attributeCreate']['errors']:
                print(f"      {error.get('field')}: {error.get('message')}")
        
        return None

    def _crear_atributo_talla(self):
        mutation = """
            mutation AttributeCreate($input: AttributeCreateInput!) {
                attributeCreate(input: $input) {
                    attribute {
                        id
                        name
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        variables = {
            "input": {
                "name": "Talla",
                "slug": "talla",
                "type": "VARIANT_TYPE",
                "inputType": "DROPDOWN",
                "valueRequired": True,
                "values": [
                    {"name": "28"},
                    {"name": "30"},
                    {"name": "32"},
                    {"name": "34"},
                ],
            }
        }

        data = self.ejecutar_mutation(mutation, variables)
        print(data)

    def _asignar_talla_a_tipo_producto(self, product_type_id, attribute_id):
        mutation = """
            mutation ProductTypeUpdate($id: ID!, $addVariantAttributes: [ID!]) {
                productTypeUpdate(id: $id, addVariantAttributes: $addVariantAttributes) {
                    productType {
                        id
                        name
                        variantAttributes {
                            id
                            name
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
            "id": product_type_id,
            "addVariantAttributes": [attribute_id]
        }

        data = self.ejecutar_mutation(mutation, variables)
        print(data)

    def _subir_imagen_producto(self, producto_id: str, imagen_cloudinary) -> bool:
        """Sube la imagen del producto a Saleor desde Cloudinary"""
        try:
            # Obtener la URL de la imagen de Cloudinary
            imagen_url = imagen_cloudinary.url
            
            if not imagen_url:
                print("   ⚠️  No hay URL de imagen disponible")
                return False
            
            print(f"   📸 Subiendo imagen desde: {imagen_url}")
            
            mutation = """
                mutation UploadProductMedia($productId: ID!, $image: String!, $alt: String) {
                    productMediaCreate(input: {product: $productId, image: $image, alt: $alt}) {
                        media {
                            id
                            url
                        }
                        errors {
                            field
                            message
                        }
                    }
                }
            """
            
            variables = {
                "productId": producto_id,
                "image": imagen_url,
                "alt": "Imagen del producto"
            }
            
            data = self.ejecutar_mutation(mutation, variables)
            
            if data and data.get('productMediaCreate', {}).get('media'):
                print(f"   ✅ Imagen subida correctamente")
                return True
            
            if data and data.get('productMediaCreate', {}).get('errors'):
                print(f"   ❌ Error subiendo imagen:")
                for error in data['productMediaCreate']['errors']:
                    print(f"      {error.get('field')}: {error.get('message')}")
            
            return False
            
        except Exception as e:
            print(f"   ❌ Error subiendo imagen: {e}")
            return False
    def sincronizar_multiples_productos(self, productos: List) -> Dict[str, int]:
        """
        Sincroniza múltiples productos a Saleor
        
        Args:
            productos: Lista de instancias del modelo Producto
            
        Returns:
            Diccionario con contadores de éxito y errores
        """
        resultados = {
            'exitosos': 0,
            'fallidos': 0,
            'total': len(productos)
        }
        
        print(f"\n{'='*60}")
        print(f"🚀 Iniciando sincronización de {resultados['total']} productos")
        print(f"{'='*60}")
        
        for i, producto in enumerate(productos, 1):
            print(f"\n[{i}/{resultados['total']}]", end=" ")
            
            if self.sincronizar_producto(producto):
                resultados['exitosos'] += 1
            else:
                resultados['fallidos'] += 1
        
        print(f"\n{'='*60}")
        print(f"✅ Sincronización completada:")
        print(f"   - Exitosos: {resultados['exitosos']}")
        print(f"   - Fallidos: {resultados['fallidos']}")
        print(f"   - Total: {resultados['total']}")
        print(f"{'='*60}\n")
        
        return resultados