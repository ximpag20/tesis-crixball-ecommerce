from django.core.management.base import BaseCommand
from catalogo.models import Producto
from catalogo.saleor_sync_service import SaleorSyncService


class Command(BaseCommand):
    help = 'Sincroniza productos de Crixball hacia Saleor'

    def add_arguments(self, parser):
        # Argumento opcional para sincronizar un producto específico
        parser.add_argument(
            '--producto-id',
            type=int,
            help='ID del producto específico a sincronizar',
        )
        
        # Argumento para sincronizar solo productos sin stock
        parser.add_argument(
            '--solo-con-stock',
            action='store_true',
            help='Sincronizar solo productos que tengan stock disponible',
        )

    def handle(self, *args, **options):
        producto_id = options.get('producto_id')
        solo_con_stock = options.get('solo_con_stock')
        
        # Crear instancia del servicio de sincronización
        sync_service = SaleorSyncService()
        
        # Banner inicial
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('🔄 SINCRONIZACIÓN CRIXBALL → SALEOR'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # Verificar si Saleor está disponible
        self.stdout.write('🔍 Verificando conexión con Saleor...')
        test_query = """
            query {
                shop {
                    name
                }
            }
        """
        test_result = sync_service.ejecutar_mutation(test_query)
        
        if not test_result:
            self.stdout.write(self.style.ERROR('\n❌ No se puede conectar con Saleor.'))
            self.stdout.write(self.style.ERROR('   Asegúrate de que Saleor esté corriendo en localhost:8001\n'))
            return
        
        shop_name = test_result.get('shop', {}).get('name', 'Desconocido')
        self.stdout.write(self.style.SUCCESS(f'✅ Conectado a: {shop_name}\n'))
        
        # Caso 1: Sincronizar un producto específico
        if producto_id:
            self.stdout.write(f'📦 Sincronizando producto ID: {producto_id}')
            
            try:
                producto = Producto.objects.get(id_pro=producto_id)
                
                if sync_service.sincronizar_producto(producto):
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Producto "{producto.nombre_pro}" sincronizado exitosamente!\n'))
                else:
                    self.stdout.write(self.style.ERROR(f'\n❌ Error sincronizando el producto "{producto.nombre_pro}"\n'))
                    
            except Producto.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'\n❌ No existe un producto con ID: {producto_id}\n'))
                return
        
        # Caso 2: Sincronizar todos los productos (con o sin filtro de stock)
        else:
            if solo_con_stock:
                self.stdout.write('📦 Obteniendo productos con stock disponible...')
                productos = Producto.objects.filter(
                    producto_tallas__cantidad_disponible__gt=0
                ).distinct()
            else:
                self.stdout.write('📦 Obteniendo todos los productos...')
                productos = Producto.objects.all()
            
            total = productos.count()
            
            if total == 0:
                self.stdout.write(self.style.WARNING('\n⚠️  No hay productos para sincronizar\n'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'✅ Se encontraron {total} productos\n'))
            
            # Confirmar antes de sincronizar
            if total > 10:
                confirmar = input(f'⚠️  ¿Deseas sincronizar {total} productos? (s/n): ')
                if confirmar.lower() != 's':
                    self.stdout.write(self.style.WARNING('\n❌ Sincronización cancelada\n'))
                    return
            
            # Sincronizar productos
            resultados = sync_service.sincronizar_multiples_productos(list(productos))
            
            # Mostrar resumen final
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE SINCRONIZACIÓN'))
            self.stdout.write('='*70)
            
            if resultados['exitosos'] > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Exitosos: {resultados['exitosos']}"))
            
            if resultados['fallidos'] > 0:
                self.stdout.write(self.style.ERROR(f"❌ Fallidos: {resultados['fallidos']}"))
            
            self.stdout.write(self.style.SUCCESS(f"📦 Total procesados: {resultados['total']}"))
            self.stdout.write('='*70 + '\n')
            
            # Mensaje de éxito o error según resultados
            if resultados['fallidos'] == 0:
                self.stdout.write(self.style.SUCCESS('🎉 ¡Sincronización completada exitosamente!\n'))
            elif resultados['exitosos'] == 0:
                self.stdout.write(self.style.ERROR('💔 No se pudo sincronizar ningún producto\n'))
            else:
                self.stdout.write(self.style.WARNING('⚠️  Sincronización completada con algunos errores\n'))
