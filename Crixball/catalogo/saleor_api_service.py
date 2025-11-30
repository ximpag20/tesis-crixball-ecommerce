import requests
from typing import List, Dict, Optional
from .saleor_auth_service import SaleorAuthService  # 🔥 NUEVO

class SaleorAPIService:
    """
    Servicio para consumir productos desde Saleor y mostrarlos en el frontend
    """
    
    def __init__(self):
        self.api_url = "http://localhost:8001/graphql/"
        self.channel = "default-channel"
        self.auth_service = SaleorAuthService()  # 🔥 NUEVO
    
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
            
            if response.status_code == 200:
                data = response.json()
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
                                'stock': variante.get('quantityAvailable', 0)
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

    def actualizar_stock_variante(self, variante_id: str, nueva_cantidad: int) -> bool:
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
        warehouse_id = "V2FyZWhvdXNlOjVjN2IyODRmLTk4YTQtNDg2YS1hZTYwLWUwMTlkZWRlZTk0Yg=="  # ID del warehouse por defecto
        
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