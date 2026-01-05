
# catalogo/checkout_service.py

import requests
import base64  # 🔥 Agregar al inicio del archivo
from typing import Optional, Dict
from .saleor_auth_service import SaleorAuthService
from .saleor_api_service import SaleorAPIService
from django.conf import settings
import json

class CheckoutService:
    """
    Servicio para manejar el flujo completo de checkout y pago en Saleor
    """
    
    def __init__(self):
        self.api_url = "http://localhost:8001/graphql/"
        self.auth_service = SaleorAuthService()
        self.last_errors = []
        self.saleor = SaleorAPIService()
    
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
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'errors' in data:
                    print(f"❌ GraphQL Errors: {data['errors']}")
                    return None
                
                if 'data' in data:
                    return data['data']
            
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return None
            
        except Exception as e:
            print(f"❌ Error ejecutando mutation: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ========================================================================
    # 🔥 PASO 1: CREAR DIRECCIÓN EN SALEOR
    # ========================================================================
    
    # catalogo/checkout_service.py

    def crear_direccion_envio(self, shipping_data: dict, user_id: str = None) -> Optional[str]:
        """
        Crea una dirección de envío en Saleor
        """
        
        # 🔥 Formatear teléfono con código de país (+593 para Ecuador)
        phone = shipping_data.get('phone', '').strip()
        
        if phone and not phone.startswith('+'):
            if shipping_data.get('country') == 'EC':
                # Limpiar espacios y caracteres especiales
                phone_digits = ''.join(filter(str.isdigit, phone))
                
                # 🔥 Si tiene 10 dígitos, eliminar el primer dígito (el 0 inicial)
                if len(phone_digits) == 10:
                    phone_digits = phone_digits[1:]  # Elimina el primer dígito
                    print(f"   📞 Teléfono original 10 dígitos: {phone}")
                    print(f"   📞 Después de quitar primer dígito: {phone_digits}")
                
                # 🔥 Si tiene 9 dígitos, está correcto
                elif len(phone_digits) == 9:
                    print(f"   📞 Teléfono ya tiene 9 dígitos: {phone_digits}")
                
                # 🔥 Si no tiene 9 o 10 dígitos, dejar como está (puede fallar la validación)
                else:
                    print(f"   ⚠️ Teléfono con longitud inesperada: {len(phone_digits)} dígitos")
                
                # Agregar código de país
                phone = f'+593{phone_digits}'
            else:
                # Para otros países, agregar + si no tiene
                phone = f'+{phone}'
        
        mutation = """
        mutation CreateAddress($input: AddressInput!) {
            accountAddressCreate(input: $input) {
                address {
                    id
                    firstName
                    lastName
                    streetAddress1
                    city
                    postalCode
                    phone
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
                "firstName": shipping_data.get('first_name'),
                "lastName": shipping_data.get('last_name'),
                "streetAddress1": shipping_data.get('street_address_1'),
                "streetAddress2": shipping_data.get('street_address_2', ''),
                "city": shipping_data.get('city'),
                "cityArea": shipping_data.get('city_area', ''),
                "postalCode": shipping_data.get('postal_code'),
                "country": shipping_data.get('country', 'EC'),
                "phone": phone,  # 🔥 Usar teléfono formateado
            }
        }
        
        print(f"📍 Creando dirección en Saleor...")
        print(f"   Variables: {variables}")
        print(f"   ✅ Teléfono final formateado: {phone}")
        
        data = self._ejecutar_mutation(mutation, variables)
        
        if not data or not data.get('accountAddressCreate'):
            print(f"❌ Error: No se pudo crear la dirección")
            return None
        
        result = data['accountAddressCreate']
        
        if result.get('errors'):
            print(f"❌ Errores al crear dirección: {result['errors']}")
            return None
        
        if result.get('address'):
            address_id = result['address']['id']
            print(f"✅ Dirección creada exitosamente: {address_id}")
            print(f"   Teléfono guardado en Saleor: {result['address'].get('phone')}")
            return address_id
        
        return None
    
    # ========================================================================
    # 🔥 PASO 2: ASIGNAR DIRECCIÓN AL CHECKOUT
    # ========================================================================

    def asignar_direccion_checkout(self, checkout_token: str, shipping_data: dict) -> bool:
        """
        Asigna dirección de envío al checkout usando la mutation correcta
        """
        self.last_errors = []  # ✅ reset por cada intento

        phone = shipping_data.get('phone', '').strip()
        if phone and not phone.startswith('+'):
            if shipping_data.get('country') == 'EC':
                phone_digits = ''.join(filter(str.isdigit, phone))
                if len(phone_digits) == 10:
                    phone_digits = phone_digits[1:]
                phone = f'+593{phone_digits}'

        mutation = """
        mutation UpdateCheckoutShippingAddress($token: UUID!, $shippingAddress: AddressInput!) {
            checkoutShippingAddressUpdate(
                token: $token
                shippingAddress: $shippingAddress
            ) {
                checkout {
                    id
                    shippingAddress {
                        firstName
                        lastName
                        city
                        country { code }
                    }
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
            "token": checkout_token,
            "shippingAddress": {
                "firstName": shipping_data.get('first_name'),
                "lastName": shipping_data.get('last_name'),
                "streetAddress1": shipping_data.get('street_address_1'),
                "streetAddress2": shipping_data.get('street_address_2', ''),
                "city": shipping_data.get('city'),
                "cityArea": shipping_data.get('city_area', ''),
                "postalCode": shipping_data.get('postal_code'),
                "country": "EC",
                "phone": phone,
            }
        }

        print(f"🛒 Asignando dirección de envío al checkout.")
        print(f"   Token: {checkout_token}")

        data = self._ejecutar_mutation(mutation, variables)

        if not data or not data.get('checkoutShippingAddressUpdate'):
            print(f"❌ Error: No se pudo asignar la dirección")
            self.last_errors = [{
                "field": "unknown",
                "message": "No se pudo asignar la dirección (sin respuesta de checkoutShippingAddressUpdate).",
                "code": "UNKNOWN"
            }]
            return False

        result = data['checkoutShippingAddressUpdate']

        if result.get('errors'):
            self.last_errors = result['errors']  # ✅ CLAVE
            print(f"❌ Errores al asignar dirección: {self.last_errors}")
            return False

        checkout = result.get('checkout', {})
        if checkout.get('shippingAddress'):
            print(f"✅ Dirección asignada al checkout correctamente")
            return True

        self.last_errors = [{
            "field": "shippingAddress",
            "message": "No se pudo confirmar la asignación de dirección.",
            "code": "NOT_SET"
        }]
        print(f"❌ No se pudo confirmar la asignación de dirección")
        return False
    
    def asignar_metodo_envio(self, checkout_token: str, shipping_cost: float = 0) -> bool:
        """
        Obtiene los métodos de envío disponibles y asigna el primero al checkout
        
        El shipping_cost es informativo - el método genérico en Saleor acepta cualquier precio.
        El costo real se refleja en el total del checkout.
        
        Args:
            checkout_token: Token del checkout
            shipping_cost: Costo de envío calculado en el frontend (informativo)
        
        Returns:
            True si fue exitoso
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        
        # 🔥 PASO 1: Obtener métodos de envío disponibles
        query = """
        query GetShippingMethods($checkoutId: ID!) {
            checkout(id: $checkoutId) {
                id
                shippingMethods {
                    id
                    name
                    price {
                        amount
                    }
                }
            }
        }
        """
        
        variables = {"checkoutId": checkout_id_base64}
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        print(f"📦 Obteniendo métodos de envío disponibles...")
        print(f"   Costo de envío calculado por frontend: ${shipping_cost}")
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            
            checkout_data = data.get('data', {}).get('checkout', {})
            shipping_methods = checkout_data.get('shippingMethods', [])
            
            if not shipping_methods:
                print(f"❌ No hay métodos de envío disponibles")
                print(f"   📋 Solución:")
                print(f"   1. Ejecuta el script para crear zona de envío en Saleor")
                print(f"   2. Verifica que la dirección tenga country='EC'")
                print(f"   3. Reinicia Saleor después de crear la zona")
                return False
            
            print(f"✅ Métodos de envío disponibles:")
            for method in shipping_methods:
                print(f"   • {method['name']} - ${method['price']['amount']}")
            
            # 🔥 PASO 2: Seleccionar el método de envío
            # Estrategia: Usar el primer método disponible (normalmente solo hay uno)
            selected_method = shipping_methods[0]
            
            # Si hay múltiples métodos, intentar buscar uno por nombre
            if len(shipping_methods) > 1:
                print(f"   ℹ️ Múltiples métodos encontrados, buscando el más apropiado...")
                
                # Buscar por nombre que contenga palabras clave
                for method in shipping_methods:
                    method_name_lower = method['name'].lower()
                    if any(keyword in method_name_lower for keyword in ['nacional', 'estándar', 'standard', 'general']):
                        selected_method = method
                        print(f"   ✅ Método seleccionado por nombre: {method['name']}")
                        break
            
            print(f"✅ Método final seleccionado: {selected_method['name']}")
            print(f"   Precio base del método en Saleor: ${selected_method['price']['amount']}")
            print(f"   Precio calculado por tu sistema: ${shipping_cost}")
            
            # 🔥 PASO 3: Asignar método de envío al checkout
            mutation = """
            mutation UpdateShippingMethod($checkoutId: ID!, $shippingMethodId: ID!) {
                checkoutDeliveryMethodUpdate(
                    id: $checkoutId
                    deliveryMethodId: $shippingMethodId
                ) {
                    checkout {
                        id
                        deliveryMethod {
                            ... on ShippingMethod {
                                id
                                name
                            }
                        }
                        totalPrice {
                            gross {
                                amount
                            }
                        }
                        shippingPrice {
                            gross {
                                amount
                            }
                        }
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
                "checkoutId": checkout_id_base64,
                "shippingMethodId": selected_method['id']
            }
            
            print(f"📤 Asignando método de envío al checkout...")
            
            response = requests.post(
                self.api_url,
                json={"query": mutation, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False
            
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            
            result = data.get('data', {}).get('checkoutDeliveryMethodUpdate', {})
            
            if result.get('errors'):
                print(f"❌ Errores al asignar método de envío: {result['errors']}")
                return False
            
            checkout = result.get('checkout', {})
            if checkout:
                shipping_price = checkout.get('shippingPrice', {}).get('gross', {}).get('amount', 0)
                total_price = checkout.get('totalPrice', {}).get('gross', {}).get('amount', 0)
                
                print(f"✅ Método de envío asignado correctamente")
                print(f"   Precio de envío en checkout: ${shipping_price}")
                print(f"   Total del checkout: ${total_price}")
            else:
                print(f"✅ Método de envío asignado correctamente")
            
            return True
            
        except Exception as e:
            print(f"❌ Error asignando método de envío: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _convertir_uuid_a_id_base64(self, uuid_string: str, tipo: str = "Checkout") -> str:
        """
        Convierte un UUID a formato base64 ID que Saleor espera
        
        Args:
            uuid_string: UUID en formato string (ej: "b0b60759-eeef-49cb-8406-58505f60ea05")
            tipo: Tipo de objeto ("Checkout", "Order", etc)
        
        Returns:
            ID en formato base64 (ej: "Q2hlY2tvdXQ6YjBiNjA3NTktZWVlZi00OWNiLTg0MDYtNTg1MDVmNjBlYTA1")
        """
        # Formato que Saleor espera: "Tipo:uuid"
        id_string = f"{tipo}:{uuid_string}"
        
        # Convertir a base64
        id_base64 = base64.b64encode(id_string.encode('utf-8')).decode('utf-8')
        
        return id_base64

    
    # ========================================================================
    # 🔥 PASO 3: CREAR PAGO CON GATEWAY DUMMY
    # ========================================================================
    
    def crear_pago_dummy(self, checkout_token: str, total_amount: float) -> Optional[Dict]:
        """
        Crea un pago usando el gateway Dummy
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        
        # 🔥 PASO 1: Obtener gateways disponibles del checkout
        print(f"🔍 Obteniendo gateways disponibles del checkout...")
        gateways = self.obtener_gateways_disponibles(checkout_token)
        
        if not gateways:
            print(f"❌ No hay gateways disponibles para este checkout")
            print(f"   Esto puede significar:")
            print(f"   1. El plugin no está activo en el channel")
            print(f"   2. El checkout no tiene items")
            print(f"   3. Hay un problema de configuración")
            return None
        
        # 🔥 PASO 2: Buscar el gateway dummy
        gateway_id = None
        for gw in gateways:
            print(f"   Gateway encontrado: {gw['id']} - {gw['name']}")
            if 'dummy' in gw['id'].lower():
                gateway_id = gw['id']
                break
        
        if not gateway_id:
            print(f"❌ Gateway dummy no encontrado en los disponibles")
            print(f"   Gateways disponibles: {[g['id'] for g in gateways]}")
            # 🔥 Usar el primer gateway disponible como fallback
            if gateways:
                gateway_id = gateways[0]['id']
                print(f"⚠️ Usando primer gateway disponible: {gateway_id}")
            else:
                return None
        
        print(f"✅ Usando gateway: {gateway_id}")
        
        # 🔥 PASO 3: Crear el pago
        mutation = """
        mutation CreatePayment($checkoutId: ID!, $input: PaymentInput!) {
            checkoutPaymentCreate(
                checkoutId: $checkoutId
                input: $input
            ) {
                payment {
                    id
                    gateway
                    isActive
                    chargeStatus
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
            "checkoutId": checkout_id_base64,
            "input": {
                "gateway": gateway_id,
                "amount": total_amount,
                "token": "dummy-token-12345",
            }
        }
        
        print(f"💳 Creando pago...")
        print(f"   Checkout ID (base64): {checkout_id_base64}")
        print(f"   Gateway ID: {gateway_id}")
        print(f"   Monto: ${total_amount}")
        
        data = self._ejecutar_mutation(mutation, variables)
        
        if not data or not data.get('checkoutPaymentCreate'):
            print(f"❌ Error: No se pudo crear el pago")
            return None
        
        result = data['checkoutPaymentCreate']
        
        if result.get('errors'):
            print(f"❌ Errores al crear pago: {result['errors']}")
            return None
        
        if result.get('payment'):
            payment = result['payment']
            print(f"✅ Pago creado: {payment['id']}")
            print(f"   Gateway: {payment['gateway']}")
            print(f"   Status: {payment['chargeStatus']}")
            
            return {
                'success': True,
                'payment_id': payment['id'],
                'status': payment['chargeStatus']
            }
        
        return None
    
    
    # ========================================================================
    # 🔥 PASO 3 (alternativo): CREAR PAGO CON STRIPE (externo)
    # ========================================================================

    def crear_pago_stripe(
        self,
        checkout_token: str,
        total_amount: float,
        stripe_payment_method_id: str
    ) -> Optional[Dict]:
        """
        Crea un pago usando Stripe directamente (PaymentIntent)
        y devuelve el ID del PaymentIntent para que después
        checkoutComplete (con paymentData) marque la orden como pagada.

        👉 OJO: aquí ya NO se llama a paymentCapture en Saleor.
        """
        import stripe

        # 🔥 Usa tu clave desde settings (NO hardcode)
        stripe.api_key = settings.STRIPE_SECRET_KEY  # <-- aquí tu .env

        # (Solo por logging, no lo necesitamos para el pago)
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")

        # 🔥 PASO 1: Crear PaymentIntent en Stripe directamente
        try:
            print(f"💳 [Stripe] Creando PaymentIntent en Stripe...")
            print(f"   Monto: ${total_amount}")
            print(f"   Payment Method: {stripe_payment_method_id}")

            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_amount * 100),  # Stripe usa centavos
                currency="usd",
                payment_method=stripe_payment_method_id,
                confirm=True,  # 🔥 Confirmar automáticamente
                automatic_payment_methods={
                    'enabled': True,
                    'allow_redirects': 'never'
                }
            )

            print(f"✅ [Stripe] PaymentIntent creado: {payment_intent.id}")
            print(f"   Status: {payment_intent.status}")

            if payment_intent.status != 'succeeded':
                print(f"❌ [Stripe] Pago no exitoso: {payment_intent.status}")
                return None

        except stripe.error.CardError as e:
            print(f"❌ [Stripe] Error con la tarjeta: {e.user_message}")
            return None
        except Exception as e:
            print(f"❌ [Stripe] Error procesando pago: {str(e)}")
            return None

        # 🔥 En este modo, NO registramos el pago extra en Saleor con checkoutPaymentCreate,
        # porque vamos a usar paymentData en checkoutComplete.
        # Saleor tratará este pago como externo (Stripe) ya capturado.

        return {
            "success": True,
            "stripe_payment_intent": payment_intent.id,
            "status": payment_intent.status,
        }

    
    # ========================================================================
    # 🔥 PASO 3.5: CAPTURAR PAGO DE STRIPE
    # ========================================================================

    def capturar_pago_stripe(self, payment_id: str) -> bool:
        """
        Captura el pago de Stripe después de crearlo
        """
        mutation = """
        mutation CapturePayment($paymentId: ID!) {
            paymentCapture(paymentId: $paymentId) {
                payment {
                    id
                    chargeStatus
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
            "paymentId": payment_id
        }
        
        print(f"💳 [Stripe] Capturando pago {payment_id}...")
        
        data = self._ejecutar_mutation(mutation, variables)

        data = self._ejecutar_mutation(mutation, variables)

        # 🔥 AGREGAR ESTAS LÍNEAS EXACTAMENTE AQUÍ:
        print(f"🔍 DEBUG - Respuesta RAW de completar orden:")
        print(f"   Type: {type(data)}")
        print(f"   Value: {data}")
        if data:
            print(f"   Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
        # 🔥 FIN DE LAS LÍNEAS A AGREGAR

        if not data or not data.get('checkoutComplete'):
            print(f"❌ Error: No se pudo completar la orden")
            return None
        
        if not data or not data.get('paymentCapture'):
            print(f"❌ [Stripe] No se pudo capturar el pago")
            return False
        
        result = data['paymentCapture']
        
        if result.get('errors'):
            print(f"❌ [Stripe] Errores al capturar: {result['errors']}")
            return False
        
        if result.get('payment'):
            payment = result['payment']
            print(f"✅ [Stripe] Pago capturado!")
            print(f"   Nuevo status: {payment['chargeStatus']}")
            return True
        
        return False
    
    # ========================================================================
    # 🔥 PASO 4: COMPLETAR ORDEN
    # ========================================================================
    
    def completar_orden(self, checkout_token: str) -> Optional[Dict]:
        """
        Completa la orden en Saleor
        
        Args:
            checkout_token: Token del checkout
        
        Returns:
            Diccionario con los datos de la orden creada
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        print(f"✅ Completando orden...")
        print(f"   Checkout UUID: {checkout_token}")
        print(f"   Checkout ID (base64): {checkout_id_base64}")

        mutation = """
        mutation CompleteCheckout($checkoutId: ID!) {
            checkoutComplete(checkoutId: $checkoutId) {
                order {
                    id
                    number
                    created
                    status
                    total {
                        gross {
                            amount
                            currency
                        }
                    }
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
            "checkoutId": checkout_id_base64
        }
        
        print(f"✅ Completando orden...")
        
        data = self._ejecutar_mutation(mutation, variables)
        
        if not data or not data.get('checkoutComplete'):
            print(f"❌ Error: No se pudo completar la orden")
            return None
        
        result = data['checkoutComplete']
        
        if result.get('errors'):
            print(f"❌ Errores al completar orden: {result['errors']}")
            return None
        
        if result.get('order'):
            order = result['order']
            print(f"✅ Orden creada exitosamente!")
            print(f"   Order ID: {order['id']}")
            print(f"   Order Number: {order['number']}")
            print(f"   Total: ${order['total']['gross']['amount']}")
            
            return {
                'success': True,
                'order_id': order['id'],
                'order_number': order['number'],
                'total': order['total']['gross']['amount'],
                'status': order['status']
            }
        
        return None

    def obtener_gateways_disponibles(self, checkout_token: str) -> Optional[list]:
        """
        Obtiene los gateways de pago disponibles para el checkout
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        
        query = """
        query GetAvailablePaymentGateways($checkoutId: ID!) {
            checkout(id: $checkoutId) {
                availablePaymentGateways {
                    id
                    name
                }
            }
        }
        """
        
        variables = {"checkoutId": checkout_id_base64}
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                gateways = data.get('data', {}).get('checkout', {}).get('availablePaymentGateways', [])
                print(f"✅ Gateways disponibles: {gateways}")
                return gateways
            
            return None
        except Exception as e:
            print(f"❌ Error obteniendo gateways: {e}")
            return None
        
    from django.conf import settings

    def descontar_stock_checkout(checkout_data):
        """
        Descuenta stock real en Saleor después de confirmar el pago
        """
        from .saleor_api_service import SaleorAPIService

        saleor = SaleorAPIService()

        for line in checkout_data["lines"]:
            variante_id = line["variant"]["id"]
            cantidad_comprada = line["quantity"]

            # Stock actual visible por Saleor
            stock_actual = line["variant"]["quantityAvailable"]

            nuevo_stock = stock_actual - cantidad_comprada

            if nuevo_stock < 0:
                raise Exception("Stock insuficiente detectado en backend")

            saleor.actualizar_stock_variante(
                variante_id,
                nuevo_stock,
                settings.SALEOR_WAREHOUSE_ID
            )
# ========================================================================
    # 🔥 ACTUALIZAR CANTIDADES DEL CHECKOUT
    # ========================================================================
    
    def actualizar_cantidades_checkout(self, checkout_token: str) -> bool:
        """
        Actualiza las cantidades del checkout según el stock real disponible
        Esto soluciona el error de stock cuando las líneas tienen cantidades obsoletas
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        
        # 1. Obtener líneas del checkout
        query = """
        query GetCheckoutLines($checkoutId: ID!) {
            checkout(id: $checkoutId) {
                lines {
                    id
                    quantity
                    variant {
                        id
                        name
                        quantityAvailable
                    }
                }
            }
        }
        """
        
        variables = {"checkoutId": checkout_id_base64}
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        print(f"🔄 Actualizando cantidades del checkout según stock disponible...")
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            
            checkout_data = data.get('data', {}).get('checkout', {})
            lines = checkout_data.get('lines', [])
            
            if not lines:
                print(f"✅ No hay líneas en el checkout")
                return True
            
            # 2. Actualizar cada línea problemática
            for line in lines:
                line_id = line['id']
                current_quantity = line['quantity']
                available_quantity = line['variant']['quantityAvailable']
                variant_name = line['variant']['name']
                
                if available_quantity == 0:
                    # Sin stock: eliminar línea
                    print(f"   ❌ {variant_name}: Sin stock, eliminando del checkout")
                    self._eliminar_linea_checkout(checkout_token, line_id)
                    
                elif current_quantity > available_quantity:
                    # Cantidad mayor que disponible: ajustar
                    print(f"   ⚠️ {variant_name}: Ajustando {current_quantity} → {available_quantity}")
                    self._actualizar_cantidad_linea(checkout_token, line_id, available_quantity)
                    
                else:
                    # Todo correcto
                    print(f"   ✅ {variant_name}: Cantidad {current_quantity} OK")
            
            print(f"✅ Checkout actualizado correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _actualizar_cantidad_linea(self, checkout_token: str, line_id: str, quantity: int) -> bool:
        """Actualiza la cantidad de una línea del checkout"""
        mutation = """
        mutation UpdateLine($token: UUID!, $lines: [CheckoutLineUpdateInput!]!) {
            checkoutLinesUpdate(token: $token, lines: $lines) {
                checkout {
                    id
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
            "lines": [{"lineId": line_id, "quantity": quantity}]
        }
        
        data = self._ejecutar_mutation(mutation, variables)
        return data is not None and not data.get('checkoutLinesUpdate', {}).get('errors')
    
    def _eliminar_linea_checkout(self, checkout_token: str, line_id: str) -> bool:
        """Elimina una línea del checkout"""
        mutation = """
        mutation DeleteLine($token: UUID!, $lineId: ID!) {
            checkoutLineDelete(token: $token, lineId: $lineId) {
                checkout {
                    id
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
            "lineId": line_id
        }
        
        data = self._ejecutar_mutation(mutation, variables)
        return data is not None and not data.get('checkoutLineDelete', {}).get('errors')
    

    def refrescar_checkout(self, checkout_token: str) -> bool:
        """
        Refresca el checkout para que Saleor recalcule el stock
        """
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        
        query = """
        query RefreshCheckout($checkoutId: ID!) {
            checkout(id: $checkoutId) {
                id
                lines {
                    id
                    quantity
                    variant {
                        id
                        name
                        quantityAvailable
                    }
                }
            }
        }
        """
        
        variables = {"checkoutId": checkout_id_base64}
        
        token = self.auth_service.obtener_token_valido()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        print(f"🔄 Refrescando checkout para recalcular stock...")
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                checkout = data.get('data', {}).get('checkout', {})
                
                if checkout:
                    lines = checkout.get('lines', [])
                    print(f"✅ Checkout refrescado: {len(lines)} línea(s)")
                    
                    for line in lines:
                        variant = line['variant']
                        print(f"   • {variant['name']}: Stock actualizado = {variant['quantityAvailable']}")
                    
                    return True
            
            print(f"❌ Error refrescando checkout")
            return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def limpiar_y_recrear_checkout(self, checkout_token_viejo: str) -> Optional[str]:
        """
        Crea un nuevo checkout copiando las líneas del checkout viejo
        Esto soluciona problemas de stock corrupto
        """
        from .saleor_api_service import SaleorAPIService
        
        print(f"🔄 Recreando checkout para solucionar problemas de stock...")
        
        # 1. Obtener datos del checkout viejo
        saleor = SaleorAPIService()
        checkout_viejo = saleor.obtener_checkout(checkout_token_viejo)
        
        if not checkout_viejo:
            print(f"❌ No se pudo obtener checkout viejo")
            return None
        
        # 2. Extraer líneas válidas
        lineas_validas = []
        for line in checkout_viejo.get('lines', []):
            variant_id = line['variant']['id']
            cantidad = line['quantity']
            disponible = line['variant']['quantityAvailable']
            
            if disponible > 0:
                cantidad_final = min(cantidad, disponible)
                lineas_validas.append({
                    'variantId': variant_id,
                    'quantity': cantidad_final
                })
                print(f"   ✅ Copiando: {line['variant']['name']} x{cantidad_final}")
            else:
                print(f"   ❌ Omitiendo: {line['variant']['name']} (sin stock)")
        
        if not lineas_validas:
            print(f"❌ No hay líneas válidas para copiar")
            return None
        
        # 3. Crear checkout nuevo
        email = checkout_viejo.get('email', '')
        
        mutation = """
        mutation CreateNewCheckout($input: CheckoutCreateInput!) {
            checkoutCreate(input: $input) {
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
        
        variables = {
            "input": {
                "channel": "default-channel",
                "email": email,
                "lines": lineas_validas
            }
        }
        
        data = self._ejecutar_mutation(mutation, variables)
        
        if not data or not data.get('checkoutCreate'):
            print(f"❌ No se pudo crear checkout nuevo")
            return None
        
        result = data['checkoutCreate']
        
        if result.get('errors'):
            print(f"❌ Errores: {result['errors']}")
            return None
        
        if result.get('checkout'):
            nuevo_token = result['checkout']['token']
            print(f"✅ Checkout nuevo creado: {nuevo_token}")
            return nuevo_token
        
        return None
    
    def limpiar_checkout_viejo(self, request) -> bool:
        """
        Elimina el checkout activo guardado en sesión (si existe)
        antes de crear uno nuevo.
        """
        try:
            checkout_token = request.session.get("checkout_token")

            if not checkout_token:
                return False

            query = """
            mutation DeleteCheckout($token: UUID!) {
            checkoutDelete(token: $token) {
                checkout {
                id
                }
                errors {
                field
                message
                }
            }
            }
            """

            variables = {"token": checkout_token}

            data = self._ejecutar_query(query, variables)
            if not data:
                return False

            errors = data.get("checkoutDelete", {}).get("errors", [])
            if errors:
                print(f"⚠️ Error eliminando checkout: {errors}")
                return False

            # Limpiar sesión
            del request.session["checkout_token"]
            del request.session["checkout_id"]
            request.session.modified = True

            print("🧹 Checkout anterior eliminado correctamente")
            return True

        except Exception as e:
            print(f"⚠️ Error limpiando checkout: {e}")
            return False
        

    def asignar_billing_address_checkout(self, checkout_id, shipping_data):
        mutation = """
        mutation SetBillingAddress($checkoutId: ID!, $address: AddressInput!) {
        checkoutBillingAddressUpdate(
            checkoutId: $checkoutId,
            billingAddress: $address
        ) {
            checkout {
            id
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
            "checkoutId": checkout_id,
            "address": {
                "firstName": shipping_data.get("first_name"),
                "lastName": shipping_data.get("last_name"),
                "streetAddress1": shipping_data.get("street_address_1"),
                "streetAddress2": shipping_data.get("street_address_2", ""),
                "city": shipping_data.get("city"),
                "cityArea": shipping_data.get("city_area", ""),
                "postalCode": shipping_data.get("postal_code"),
                "country": shipping_data.get("country", "EC"),
                "phone": shipping_data.get("phone"),
            }
        }

        data = self.saleor._ejecutar_query(mutation, variables)

        if not data:
            return False

        errors = data["checkoutBillingAddressUpdate"].get("errors", [])
        if errors:
            print("❌ Error asignando billing address:", errors)
            return False

        return True

    def completar_orden_stripe(self, checkout_token, payment_intent_id, total_amount):
        import json
        from .saleor_api_service import SaleorAPIService

        print("✅ PASO 4: Completando orden.\n")
        print("==========================================================")
        print("💳 [Stripe] Procesando finalización de compra")
        print("==========================================================\n")

        print(f"🔐 Checkout token: {checkout_token}")

        saleor = SaleorAPIService()

        # 1️⃣ Convertir checkout UUID a Base64 para Saleor
        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")
        print(f"🧬 checkoutId Base64: {checkout_id_base64}")

        # 2️⃣ Crear Payment Interno en Saleor
        print("🟢 Registrando pago interno en Saleor...")
        payment_result = saleor.crear_pago_saleor_stripe(
            checkout_id_base64=checkout_id_base64,
            amount=float(total_amount)
        )
        print("🟢 Resultado checkoutPaymentCreate:", payment_result)

        if not payment_result or payment_result.get("checkoutPaymentCreate", {}).get("errors"):
            print("❌ Saleor no creó el Payment.")
            return None

        payment_id = payment_result["checkoutPaymentCreate"]["payment"]["id"]

        # 3️⃣ Registrar transacción CAPTURE SUCCESS (esto es CLAVE)
        print("💳 Registrando transacción como pagada en Saleor...")
        tx = saleor.registrar_transaccion_stripe(checkout_id_base64, total_amount)

        print("🧾 resultado transactionCreate:", tx)

        
        if not tx or tx.get("transactionCreate", {}).get("errors"):
            print("❌ Error creando transacción.")
            return None

        transaction_id = tx["transactionCreate"]["transaction"]["id"]
        print("⚡ Transacción creada:", transaction_id)
        # 4️⃣ Ejecutar checkoutComplete con paymentData externo
        payment_data = {
            "id": payment_intent_id,
            "kind": "EXTERNAL",
            "status": "SUCCESS",
            "amount": float(total_amount),
            "currency": "USD"
        }

        print("\n🚀 Enviando checkoutComplete con paymentData a Saleor...")
        print(json.dumps(payment_data))

        # 🔥 Ahora sí ejecutamos checkoutComplete
        complete_result = saleor.completar_checkout_stripe_paymentData(
            checkout_token=checkout_token,
            payment_intent_id=payment_intent_id,
            amount=float(total_amount),
        )

        print("📌 Resultado checkoutComplete Stripe:", complete_result)

        if not complete_result or not complete_result.get("success"):
            print("❌ Error completando el checkout en Saleor:", complete_result)
            return None

        print("🎉 ORDEN GENERADA EXITOSAMENTE ✔")
        return complete_result



    # ==========================================================
    # 🔥 REGISTRAR EL PAGO STRIPE DENTRO DE SALEOR (OBLIGATORIO)
    # ==========================================================

    def crear_pago_saleor_stripe(self, checkout_token, amount):
        """
        Crear el registro del pago en Saleor usando Stripe.
        Esto NO cobra, solo registra el pago para poder usar paymentData.
        """

        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")

        mutation = """
        mutation CreatePaymentStripe($checkoutId: ID!, $input: PaymentInput!) {
            checkoutPaymentCreate(
                checkoutId: $checkoutId,
                input: $input
            ) {
                payment {
                    id
                    gateway
                    chargeStatus
                    total {
                        amount
                        currency
                    }
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
            "checkoutId": checkout_id_base64,
            "input": {
                "gateway": "saleor.payments.stripe",   # <--- tu gateway detectado correctamente
                "amount": float(amount),
                "token": "stripe-external-payment",   # no importa el token, solo registro
            }
        }

        print("💳 Ejecutando checkoutPaymentCreate para Stripe...")
        data = self._ejecutar_mutation(mutation, variables)

        if not data or not data.get("checkoutPaymentCreate"):
            print("❌ No se pudo crear el pago Stripe en Saleor")
            return None

        result = data["checkoutPaymentCreate"]

        if result.get("errors"):
            print("❌ Error Stripe interno:", result["errors"])
            return None

        print("🟢 Pago Stripe registrado internamente:", result["payment"])
        return result["payment"]


    def completar_orden_paypal(self, checkout_token, transaction_id, amount, currency="USD"):
        import json

        mutation = """
        mutation CheckoutComplete($checkoutId: ID!, $paymentData: JSONString!) {
            checkoutComplete(
                id: $checkoutId
                paymentData: $paymentData
            ) {
                order { id number status }
                confirmationNeeded
                errors { field message code }
            }
        }
        """

        checkout_id_base64 = self._convertir_uuid_a_id_base64(checkout_token, "Checkout")

        payment_data_string = json.dumps({
            "id": transaction_id,
            "kind": "EXTERNAL",
            "status": "SUCCESS",
            "amount": float(amount),
            "currency": currency
        }, ensure_ascii=False)

        variables = {
            "checkoutId": checkout_id_base64,
            "paymentData": payment_data_string
        }

        print("🚀 Completando orden PayPal en Saleor")
        print("🧾 paymentData:", payment_data_string)

        data = self._ejecutar_mutation(mutation, variables)

        if not data or not data.get("checkoutComplete"):
            return {"success": False, "error": "checkoutComplete falló (respuesta vacía)"}

        result = data["checkoutComplete"]

        if result.get("errors"):
            return {"success": False, "errors": result["errors"]}

        # ✅ Si viene order, excelente
        if result.get("order"):
            order = result["order"]
            return {
                "success": True,
                "order_id": order["id"],
                "order_number": order["number"],
                "status": order["status"],
            }

        # ✅ Si order viene null pero NO hay errors, asumimos que completó
        return {
            "success": True,
            "order_id": None,
            "order_number": None,
            "status": "COMPLETED",
            "note": "checkoutComplete no devolvió order pero tampoco errores"
        }


