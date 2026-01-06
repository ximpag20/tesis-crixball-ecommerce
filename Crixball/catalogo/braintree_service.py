import braintree
from django.conf import settings

class BraintreeService:
    def __init__(self):
        """Inicializar gateway de Braintree"""
        self.gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                environment=braintree.Environment.Sandbox,
                merchant_id=settings.BRAINTREE_MERCHANT_ID,
                public_key=settings.BRAINTREE_PUBLIC_KEY,
                private_key=settings.BRAINTREE_PRIVATE_KEY
            )
        )
    
    def generar_client_token(self):
        """Generar token de cliente para el frontend"""
        try:
            client_token = self.gateway.client_token.generate()

            print(f"✅ Client token generado (merchant=crixball): {client_token[:50]}...")
            return client_token
        except Exception as e:
            print(f"❌ Error generando client token: {e}")
            return None

    
    def procesar_pago_paypal(self, nonce, amount):
        """Procesar pago con PayPal nonce"""
        try:
            print(f"💳 Procesando pago PayPal: ${amount} con nonce: {nonce[:20]}...")
            
            result = self.gateway.transaction.sale({
                'amount': str(amount),
                'payment_method_nonce': nonce,
                'merchant_account_id': 'crixball',  # 🔥 MISMO MERCHANT
                'options': {
                    'submit_for_settlement': True
                }
            })

            
            if result.is_success:
                print(f"✅ Pago exitoso. Transaction ID: {result.transaction.id}")
                return {
                    'success': True,
                    'transaction_id': result.transaction.id,
                    'amount': result.transaction.amount,
                    'currency': 'USD'
                }
            else:
                print(f"❌ Error en pago: {result.message}")
                return {
                    'success': False,
                    'error': result.message
                }
        except Exception as e:
            print(f"❌ Excepción procesando pago: {e}")
            return {
                'success': False,
                'error': str(e)
            }