from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging
import threading
import time

# Configurar logger
logger = logging.getLogger(__name__)

# Flag para evitar sincronización recursiva
_sincronizacion_en_progreso = False

# Diccionario para rastrear productos pendientes de sincronización
_productos_pendientes = {}
_lock = threading.Lock()


def sincronizar_producto_diferido(producto_id):
    """
    Espera un momento y luego sincroniza el producto.
    Esto permite que se agreguen todas las tallas antes de sincronizar.
    """
    # Esperar 3 segundos para que se terminen de guardar todas las tallas
    time.sleep(3)
    
    global _sincronizacion_en_progreso
    
    if _sincronizacion_en_progreso:
        return
    
    try:
        _sincronizacion_en_progreso = True
        
        from .models import Producto
        from .saleor_sync_service import SaleorSyncService
        
        # Verificar si el producto aún está pendiente
        with _lock:
            if producto_id not in _productos_pendientes:
                return
            del _productos_pendientes[producto_id]
        
        # Obtener el producto
        producto = Producto.objects.get(id_pro=producto_id)
        
        # Verificar que tenga al menos una talla antes de sincronizar
        if not producto.producto_tallas.exists():
            logger.info(f"⚠️  Producto {producto.nombre_pro} sin tallas, esperando...")
            return
        
        # Crear instancia del servicio
        sync_service = SaleorSyncService()
        
        logger.info(f"🔄 Sincronizando automáticamente: {producto.nombre_pro}")
        
        # Sincronizar el producto
        exito = sync_service.sincronizar_producto(producto)
        
        if exito:
            logger.info(f"✅ Producto sincronizado con Saleor: {producto.nombre_pro}")
            print(f"\n✅ ¡Producto '{producto.nombre_pro}' sincronizado automáticamente con Saleor!\n")
        else:
            logger.warning(f"⚠️  No se pudo sincronizar: {producto.nombre_pro}")
            print(f"\n⚠️  No se pudo sincronizar '{producto.nombre_pro}' con Saleor\n")
            
    except Exception as e:
        logger.error(f"❌ Error en sincronización automática: {e}")
        print(f"\n❌ Error en sincronización: {e}\n")
    finally:
        _sincronizacion_en_progreso = False


@receiver(post_save, sender='catalogo.ProductoTalla')
def sincronizar_talla_a_saleor(sender, instance, created, **kwargs):
    """
    Signal que se ejecuta después de guardar una talla de producto.
    Programa la sincronización del producto completo después de un breve delay.
    """
    global _sincronizacion_en_progreso
    
    # Evitar sincronización si ya hay una en progreso
    if _sincronizacion_en_progreso:
        return
    
    # Solo sincronizar cuando se CREA una nueva talla
    if not created:
        return
    
    producto = instance.producto
    producto_id = producto.id_pro
    
    with _lock:
        # Si ya hay un thread de sincronización programado, no crear otro
        if producto_id in _productos_pendientes:
            logger.info(f"📦 Talla agregada: {instance.talla.talla} (sincronización ya programada)")
            return
        
        # Marcar el producto como pendiente
        _productos_pendientes[producto_id] = True
    
    logger.info(f"📦 Talla agregada: {instance.talla.talla} para {producto.nombre_pro}")
    logger.info(f"⏳ Sincronización programada en 3 segundos (esperando más tallas...)")
    
    # Iniciar thread para sincronización diferida
    thread = threading.Thread(target=sincronizar_producto_diferido, args=(producto_id,))
    thread.daemon = True
    thread.start()


@receiver(post_delete, sender='catalogo.ProductoTalla')
def sincronizar_eliminacion_talla(sender, instance, **kwargs):
    """
    Signal que se ejecuta después de eliminar una talla.
    Sincroniza las variantes actualizadas a Saleor.
    """
    global _sincronizacion_en_progreso
    
    # Evitar sincronización recursiva
    if _sincronizacion_en_progreso:
        return
    
    try:
        _sincronizacion_en_progreso = True
        
        from .saleor_sync_service import SaleorSyncService
        
        producto = instance.producto
        
        # Crear instancia del servicio
        sync_service = SaleorSyncService()
        
        logger.info(f"🗑️  Talla eliminada: {instance.talla.talla} de {producto.nombre_pro}")
        logger.info(f"🔄 Sincronizando cambios con Saleor...")
        
        # Sincronizar el producto completo
        exito = sync_service.sincronizar_producto(producto)
        
        if exito:
            logger.info(f"✅ Cambios sincronizados para: {producto.nombre_pro}")
        else:
            logger.warning(f"⚠️  No se pudieron sincronizar los cambios de: {producto.nombre_pro}")
            
    except Exception as e:
        logger.error(f"❌ Error en sincronización automática tras eliminación: {e}")
    finally:
        _sincronizacion_en_progreso = False


# ============================================================================
# NOTA IMPORTANTE SOBRE SINCRONIZACIÓN AUTOMÁTICA
# ============================================================================
# 
# Los signals sincronizan automáticamente cuando:
# - Se agrega una nueva talla (espera 3 segundos para agrupar tallas múltiples)
# - Se elimina una talla
# 
# NO sincroniza cuando solo se guarda el producto (sin tallas).
# Esto evita sincronizaciones innecesarias.
# 
# Si prefieres sincronización manual, usa: python manage.py sync_to_saleor
# 
# ============================================================================