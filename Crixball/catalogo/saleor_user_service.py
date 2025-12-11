# catalogo/saleor_user_service.py

import requests
from typing import Optional, Dict
from registro.models import Usuario
from .saleor_auth_service import SaleorAuthService

class SaleorUserService:
    """
    Servicio para sincronizar usuarios de Django con Saleor.
    
    Estrategia: Sincronización bajo demanda (lazy sync)
    - Los usuarios se crean en Saleor solo cuando acceden al catálogo/carrito
    - Django es la fuente de verdad para información de usuarios
    - Saleor solo almacena lo necesario para e-commerce
    """
    
    def __init__(self):
        self.api_url = "http://localhost:8001/graphql/"
        self.auth_service = SaleorAuthService()
    
    def _ejecutar_mutation(self, mutation: str, variables: dict = None) -> Optional[dict]:
        """Ejecuta una mutation GraphQL en Saleor"""
        payload = {"query": mutation}
        if variables:
            payload["variables"] = variables
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Respuesta completa: {data}")
                if 'data' in data:
                    return data['data']
                elif 'errors' in data:
                    print(f"❌ Error en mutation: {data['errors']}")
            
            return None
            
        except Exception as e:
            print(f"❌ Error ejecutando mutation: {e}")
            return None
    
    def _ejecutar_query(self, query: str, variables: dict = None) -> Optional[dict]:
        """Ejecuta una query GraphQL en Saleor"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
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
    
    def buscar_usuario_saleor(self, email: str) -> Optional[Dict]:
        """
        Busca un usuario en Saleor por su email
        
        Returns:
            Dict con datos del usuario o None si no existe
        """
        query = """
        query GetCustomer($email: String!) {
            customers(first: 1, filter: { search: $email }) {
                edges {
                    node {
                        id
                        email
                        firstName
                        lastName
                        isActive
                    }
                }
            }
        }
        """
        
        variables = {"email": email}
        data = self._ejecutar_query(query, variables)
        
        if data and data.get('customers') and data['customers'].get('edges'):
            edges = data['customers']['edges']
            if len(edges) > 0:
                return edges[0]['node']
        
        return None
    
    def crear_usuario_saleor(self, usuario: Usuario) -> Optional[str]:
        """
        Crea un usuario en Saleor basado en el modelo Usuario de Django
        
        Args:
            usuario: Instancia del modelo Usuario de Django
            
        Returns:
            ID del usuario creado en Saleor o None si falla
        """
        mutation = """
        mutation CreateCustomer($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user {
                    id
                    email
                    firstName
                    lastName
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
            "input": {
                "email": usuario.email,
                "firstName": usuario.nombre,
                "lastName": usuario.apellido,
                "isActive": True,
                # Nota: Saleor no almacena contraseñas de usuarios creados por API
                # La autenticación sigue siendo responsabilidad de Django
            }
        }
        
        data = self._ejecutar_mutation(mutation, variables)
        
        if data and data.get('customerCreate'):
            result = data['customerCreate']
            
            if result.get('errors'):
                print(f"❌ Errores al crear usuario: {result['errors']}")
                return None
            
            if result.get('user'):
                saleor_user_id = result['user']['id']
                print(f"✅ Usuario creado en Saleor: {usuario.email} -> ID: {saleor_user_id}")
                return saleor_user_id
        
        return None
    
    def sincronizar_usuario(self, email: str) -> Optional[str]:
        """
        Sincroniza un usuario de Django a Saleor (bajo demanda)
        
        1. Busca el usuario en Django
        2. Verifica si existe en Saleor
        3. Si no existe, lo crea
        
        Args:
            email: Email del usuario a sincronizar
            
        Returns:
            ID del usuario en Saleor o None si falla
        """
        try:
            # 1. Buscar usuario en Django
            usuario = Usuario.objects.get(email=email)
            print(f"🔍 Usuario encontrado en Django: {usuario.email}")
            
            # 2. Verificar si existe en Saleor
            usuario_saleor = self.buscar_usuario_saleor(email)
            
            if usuario_saleor:
                print(f"✅ Usuario ya existe en Saleor: {usuario_saleor['id']}")
                return usuario_saleor['id']
            
            # 3. Crear en Saleor si no existe
            print(f"➕ Creando usuario en Saleor...")
            saleor_id = self.crear_usuario_saleor(usuario)
            
            return saleor_id
            
        except Usuario.DoesNotExist:
            print(f"❌ Usuario no encontrado en Django: {email}")
            return None
        except Exception as e:
            print(f"❌ Error sincronizando usuario: {e}")
            return None
    
    def actualizar_usuario_saleor(self, email: str) -> bool:
        """
        Actualiza los datos de un usuario en Saleor desde Django
        
        Args:
            email: Email del usuario a actualizar
            
        Returns:
            True si la actualización fue exitosa
        """
        try:
            # Buscar usuario en Django
            usuario = Usuario.objects.get(email=email)
            
            # Buscar usuario en Saleor
            usuario_saleor = self.buscar_usuario_saleor(email)
            
            if not usuario_saleor:
                print(f"❌ Usuario no existe en Saleor: {email}")
                return False
            
            mutation = """
            mutation UpdateCustomer($id: ID!, $input: CustomerInput!) {
                customerUpdate(id: $id, input: $input) {
                    user {
                        id
                        email
                        firstName
                        lastName
                    }
                    errors {
                        field
                        message
                    }
                }
            }
            """
            
            variables = {
                "id": usuario_saleor['id'],
                "input": {
                    "firstName": usuario.nombre,
                    "lastName": usuario.apellido,
                }
            }
            
            data = self._ejecutar_mutation(mutation, variables)
            
            if data and data.get('customerUpdate'):
                if data['customerUpdate'].get('errors'):
                    print(f"❌ Errores actualizando: {data['customerUpdate']['errors']}")
                    return False
                
                print(f"✅ Usuario actualizado en Saleor: {email}")
                return True
            
            return False
            
        except Usuario.DoesNotExist:
            print(f"❌ Usuario no encontrado en Django: {email}")
            return False
        except Exception as e:
            print(f"❌ Error actualizando usuario: {e}")
            return False
    
    def obtener_direcciones_usuario(self, saleor_user_id: str) -> list:
        """
        Obtiene las direcciones guardadas de un usuario en Saleor
        
        Returns:
            Lista de direcciones del usuario
        """
        query = """
        query GetUserAddresses($id: ID!) {
            user(id: $id) {
                addresses {
                    id
                    firstName
                    lastName
                    streetAddress1
                    streetAddress2
                    city
                    postalCode
                    country {
                        code
                        country
                    }
                    phone
                }
            }
        }
        """
        
        variables = {"id": saleor_user_id}
        data = self._ejecutar_query(query, variables)
        
        if data and data.get('user') and data['user'].get('addresses'):
            return data['user']['addresses']
        
        return []
    
    # catalogo/saleor_user_service.py

    # 🔥 NUEVA IMPLEMENTACIÓN: customerCreate + password directo
    def crear_usuario_saleor_con_password(self, usuario: Usuario, password: str) -> Optional[Dict]:
        """
        Crea un usuario en Saleor y establece su contraseña
        
        ESTRATEGIA:
        PASO 1: Crear usuario con customerCreate (GraphQL)
        PASO 2: Establecer contraseña directamente en la base de datos
        """
        
        # PASO 1: Crear usuario
        mutation_crear = """
        mutation CreateCustomer($input: UserCreateInput!) {
            customerCreate(input: $input) {
                user {
                    id
                    email
                    firstName
                    lastName
                    isActive
                }
                errors {
                    field
                    message
                    code
                }
            }
        }
        """
        
        variables_crear = {
            "input": {
                "email": usuario.email,
                "firstName": usuario.nombre,
                "lastName": usuario.apellido,
                "isActive": True,
            }
        }
        
        print(f"🚀 PASO 1: Creando usuario en Saleor: {usuario.email}")
        
        data = self._ejecutar_mutation(mutation_crear, variables_crear)
        
        if not data or not data.get('customerCreate'):
            print(f"❌ Error en PASO 1: No se pudo crear usuario")
            return None
        
        result = data['customerCreate']
        
        if result.get('errors'):
            print(f"❌ Errores en PASO 1: {result['errors']}")
            return None
        
        if not result.get('user'):
            print(f"❌ No se obtuvo usuario en PASO 1")
            return None
        
        user_id = result['user']['id']
        print(f"✅ PASO 1 completado: Usuario creado con ID {user_id}")
        
        # PASO 2: Establecer contraseña directamente en la base de datos
        print(f"🔐 PASO 2: Estableciendo contraseña en base de datos...")
        
        if self._establecer_password_db(usuario.email, password):
            print(f"✅ PASO 2 completado: Contraseña establecida")
            print(f"✅ Usuario registrado exitosamente y puede hacer login: {usuario.email}")
            
            return {
                'user': result['user'],
                'requiresConfirmation': False
            }
        else:
            print(f"❌ Error en PASO 2: No se pudo establecer contraseña")
            return None

    def _establecer_password_db(self, email: str, password: str) -> bool:
        """
        Establece la contraseña y CONFIRMA la cuenta en la base de datos de Saleor
        """
        try:
            from django.contrib.auth.hashers import make_password
            import psycopg2
            
            # Configuración de conexión a la base de datos de Saleor
            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                database="saleor_db",
                user="postgres",
                password="1234"
            )
            
            cursor = conn.cursor()
            
            # Generar hash de contraseña compatible con Django/Saleor
            password_hash = make_password(password)
            
            print(f"   🔹 Generando hash de contraseña...")
            print(f"   🔹 Actualizando usuario: {email}")
            
            # 🔥 ACTUALIZAR: Contraseña + Confirmar cuenta
            cursor.execute("""
                UPDATE account_user 
                SET password = %s, 
                    is_confirmed = TRUE
                WHERE email = %s
            """, (password_hash, email))
            
            affected_rows = cursor.rowcount
            conn.commit()
            
            print(f"   🔹 Filas afectadas: {affected_rows}")
            
            cursor.close()
            conn.close()
            
            if affected_rows > 0:
                print(f"   ✅ Contraseña y confirmación actualizadas en la base de datos")
                return True
            else:
                print(f"   ⚠️ No se encontró el usuario en account_user")
                return False
        
        except ImportError as e:
            print(f"   ❌ Error: psycopg2 no está instalado")
            print(f"   💡 Ejecuta: pip install psycopg2-binary")
            return False
        
        except Exception as e:
            print(f"   ❌ Error estableciendo contraseña en base de datos: {e}")
            import traceback
            traceback.print_exc()
            return False

    # 🔥 NUEVO: Autenticar usuario con Saleor
    def autenticar_usuario_saleor(self, email: str, password: str) -> Optional[Dict]:
        """
        Autentica un usuario contra Saleor y obtiene token de acceso
        
        Args:
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Dict con token, refresh token y datos del usuario, o None si falla
        """
        mutation = """
        mutation TokenCreate($email: String!, $password: String!) {
            tokenCreate(email: $email, password: $password) {
                token
                refreshToken
                csrfToken
                user {
                    id
                    email
                    firstName
                    lastName
                    isActive
                    isStaff
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
            "email": email,
            "password": password
        }
        
        print(f"🔐 Autenticando usuario en Saleor: {email}")
        
        # Para login, NO usar token de autenticación previo
        payload = {"query": mutation, "variables": variables}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data'].get('tokenCreate'):
                    result = data['data']['tokenCreate']
                    
                    if result.get('errors'):
                        print(f"❌ Errores de autenticación: {result['errors']}")
                        return None
                    
                    if result.get('token') and result.get('user'):
                        print(f"✅ Usuario autenticado en Saleor: {email}")
                        return result
                
                print(f"❌ Respuesta inesperada: {data}")
                return None
            
            print(f"❌ Error HTTP {response.status_code}")
            return None
            
        except Exception as e:
            print(f"❌ Error autenticando en Saleor: {e}")
            return None
    
    # catalogo/saleor_user_service.py

    def obtener_usuario_actual(self, token: str) -> Optional[Dict]:
        """
        Obtiene datos del usuario autenticado usando su token
        
        Args:
            token: Token de acceso del usuario
            
        Returns:
            Dict con datos del usuario o None
        """
        query = """
        query GetMe {
            me {
                id
                email
                firstName
                lastName
                isActive
                isStaff
                dateJoined
                lastLogin
                defaultShippingAddress {
                    id
                    firstName
                    lastName
                    streetAddress1
                    city
                    postalCode
                    country {
                        code
                        country
                    }
                    phone
                }
                addresses {
                    id
                    firstName
                    lastName
                    streetAddress1
                    city
                    postalCode
                    phone
                }
            }
        }
        """
        
        print(f"🔵 obtener_usuario_actual - Iniciando...")  # 🔥 DEBUG
        print(f"🔑 Token recibido (primeros 30 chars): {token[:30] if token else 'None'}")  # 🔥 DEBUG
        
        payload = {"query": query}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            print(f"📤 Enviando request a Saleor...")  # 🔥 DEBUG
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            print(f"📥 Status Code: {response.status_code}")  # 🔥 DEBUG
            
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Respuesta JSON: {data}")  # 🔥 DEBUG
                
                if 'data' in data and data['data'].get('me'):
                    usuario = data['data']['me']
                    print(f"✅ Usuario obtenido de Saleor: {usuario.get('email')}")  # 🔥 DEBUG
                    return usuario
                else:
                    print(f"⚠️ Respuesta de Saleor no contiene 'me'")  # 🔥 DEBUG
                    print(f"📊 Estructura de respuesta: {data.keys() if data else 'None'}")  # 🔥 DEBUG
            else:
                print(f"❌ Error HTTP {response.status_code}")  # 🔥 DEBUG
                print(f"📥 Respuesta: {response.text[:200]}")  # 🔥 DEBUG
            
            return None
            
        except Exception as e:
            print(f"❌ Error obteniendo usuario: {e}")
            import traceback
            traceback.print_exc()  # 🔥 DEBUG
            return None
    
    # 🔥 NUEVO: Verificar si usuario existe en Saleor por email
    def usuario_existe_en_saleor(self, email: str) -> bool:
        """
        Verifica si un usuario existe en Saleor
        
        Args:
            email: Email a verificar
            
        Returns:
            True si existe, False si no
        """
        usuario = self.buscar_usuario_saleor(email)
        return usuario is not None    

    def refrescar_token_usuario(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresca el token de acceso del usuario usando el refresh token
        
        Args:
            refresh_token: Refresh token obtenido en el login
            
        Returns:
            Dict con nuevo token y refresh token, o None si falla
        """
        mutation = """
        mutation TokenRefresh($refreshToken: String!) {
            tokenRefresh(refreshToken: $refreshToken) {
                token
                errors {
                    field
                    message
                    code
                }
            }
        }
        """
        
        variables = {
            "refreshToken": refresh_token
        }
        
        print(f"🔄 Refrescando token de usuario...")
        
        payload = {"query": mutation, "variables": variables}
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data'].get('tokenRefresh'):
                    result = data['data']['tokenRefresh']
                    
                    if result.get('errors'):
                        print(f"❌ Error refrescando token: {result['errors']}")
                        return None
                    
                    if result.get('token'):
                        print(f"✅ Token refrescado exitosamente")
                        return result
                
                print(f"❌ Respuesta inesperada: {data}")
                return None
            
            print(f"❌ Error HTTP {response.status_code}")
            return None
            
        except Exception as e:
            print(f"❌ Error refrescando token: {e}")
            return None
    
    # 🔥 NUEVO: Verificar si token está expirado
    def verificar_token_valido(self, token: str) -> bool:
        """
        Verifica si un token aún es válido
        
        Args:
            token: Token a verificar
            
        Returns:
            True si es válido, False si expiró
        """
        query = """
        query VerifyToken {
            me {
                id
                email
            }
        }
        """
        
        payload = {"query": query}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Si devuelve datos del usuario, el token es válido
                return 'data' in data and data['data'].get('me') is not None
            
            return False
            
        except Exception as e:
            print(f"❌ Error verificando token: {e}")
            return False