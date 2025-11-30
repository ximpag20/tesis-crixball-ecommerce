import requests
from datetime import datetime, timedelta
from django.core.cache import cache
import json
from django.conf import settings  # 🔥 NUEVO


class SaleorAuthService:
    """
    Servicio para manejar autenticación con Saleor usando refresh tokens
    """
    
    def __init__(self):
        self.api_url = settings.SALEOR_API_URL  # 🔥 DESDE SETTINGS
        self.user_email = settings.SALEOR_USER_EMAIL  # 🔥 DESDE SETTINGS
        self.user_password = settings.SALEOR_USER_PASSWORD  # 🔥 DESDE SETTINGS
        self.cache_key_access = "saleor_access_token"
        self.cache_key_refresh = "saleor_refresh_token"
    
    def _ejecutar_mutation(self, mutation: str, variables: dict = None) -> dict:
        """Ejecuta una mutation en Saleor"""
        payload = {"query": mutation}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"❌ Error ejecutando mutation: {e}")
            return None
    
    def obtener_tokens_iniciales(self) -> dict:
        """
        Obtiene tokens iniciales con email y password
        """
        mutation = """
            mutation TokenCreate($email: String!, $password: String!) {
                tokenCreate(email: $email, password: $password) {
                    token
                    refreshToken
                    user {
                        email
                    }
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "email": self.user_email,
            "password": self.user_password
        }
        
        result = self._ejecutar_mutation(mutation, variables)
        
        if result and 'data' in result:
            token_data = result['data']['tokenCreate']
            
            if not token_data.get('errors'):
                access_token = token_data['token']
                refresh_token = token_data['refreshToken']
                
                # Guardar en cache (expira en 5 minutos antes del tiempo real)
                cache.set(self.cache_key_access, access_token, timeout=295)  # 4:55 min
                cache.set(self.cache_key_refresh, refresh_token, timeout=86400)  # 24 horas
                
                print("✅ Tokens obtenidos exitosamente")
                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }
            else:
                print(f"❌ Error obteniendo tokens: {token_data['errors']}")
                return None
        
        return None
    
    def refrescar_token(self) -> str:
        """
        Refresca el access token usando el refresh token
        """
        refresh_token = cache.get(self.cache_key_refresh)
        
        if not refresh_token:
            print("⚠️ No hay refresh token, obteniendo tokens iniciales...")
            tokens = self.obtener_tokens_iniciales()
            return tokens['access_token'] if tokens else None
        
        mutation = """
            mutation TokenRefresh($refreshToken: String!) {
                tokenRefresh(refreshToken: $refreshToken) {
                    token
                    errors {
                        field
                        message
                    }
                }
            }
        """
        
        variables = {
            "refreshToken": refresh_token
        }
        
        result = self._ejecutar_mutation(mutation, variables)
        
        if result and 'data' in result:
            token_data = result['data']['tokenRefresh']
            
            if not token_data.get('errors'):
                access_token = token_data['token']
                
                # Guardar nuevo access token
                cache.set(self.cache_key_access, access_token, timeout=295)
                
                print("✅ Access token refrescado")
                return access_token
            else:
                print(f"❌ Error refrescando token: {token_data['errors']}")
                # Si falla, obtener tokens nuevos
                tokens = self.obtener_tokens_iniciales()
                return tokens['access_token'] if tokens else None
        
        return None
    
    def obtener_token_valido(self) -> str:
        """
        Obtiene un token válido, refrescándolo automáticamente si es necesario
        """
        # Intentar obtener token del cache
        access_token = cache.get(self.cache_key_access)
        
        if access_token:
            print("✅ Usando token en cache")
            return access_token
        
        # Si no hay token en cache, intentar refrescar
        print("⚠️ Token expirado, refrescando...")
        access_token = self.refrescar_token()
        
        return access_token