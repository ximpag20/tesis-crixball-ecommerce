import cloudinary
from django.db import models
from cloudinary.models import CloudinaryField

class Talla(models.Model):
    id_talla = models.AutoField(primary_key=True)
    talla = models.CharField(max_length=10)  # Puede ser número o texto (e.g., S, M, L)

    def __str__(self):
        return self.talla
    
    class Meta:
        db_table = 'talla'

class Categoria(models.Model):
    id_cat = models.AutoField(primary_key=True)
    nombre_cat = models.CharField(max_length=255)

    def __str__(self):
        return self.nombre_cat
    
    class Meta:
        db_table = 'categoria' 


class Rama(models.Model):
    id_rama = models.CharField(max_length=4, primary_key=True)
    nombre_rama = models.CharField(max_length=255)
    id_cat = models.ForeignKey(Categoria, on_delete=models.CASCADE, db_column='id_cat')

    def __str__(self):
        return self.nombre_rama
    
    class Meta:
        db_table = 'rama' 


class Producto(models.Model):
    id_pro = models.AutoField(primary_key=True)
    nombre_pro = models.CharField(max_length=255)
    detalle_pro = models.TextField()
    imagen_pro = CloudinaryField('image', null=True, blank=True)  # Usa CloudinaryField
    id_rama = models.ForeignKey(Rama, on_delete=models.CASCADE, db_column='id_rama')
    saleor_product_id = models.CharField(max_length=100, null=True, blank=True, unique=True)  # NUEVO CAMPO
    def __str__(self):
        return self.nombre_pro
    
    class Meta:
        db_table = 'producto' 

class ProductoTalla(models.Model):
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.CASCADE, related_name='producto_tallas')
    talla = models.ForeignKey('catalogo.Talla', on_delete=models.CASCADE, related_name='talla_productos')
    cantidad_disponible = models.PositiveIntegerField(default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.producto.nombre_pro} - {self.talla.talla} (Cantidad: {self.cantidad_disponible}, Precio: {self.precio})"
    
    def sincronizar_stock_con_saleor(self):
        """
        Sincroniza el stock de Django con Saleor cuando cambia
        """
        if not self.producto.saleor_product_id:
            return False
        
        from .saleor_api_service import SaleorAPIService
        
        # Obtener producto de Saleor
        saleor_service = SaleorAPIService()
        producto_saleor = saleor_service.obtener_producto_por_id(self.producto.saleor_product_id)
        
        if not producto_saleor:
            return False
        
        # Buscar la variante correspondiente a esta talla
        for talla_data in producto_saleor.get('tallas', []):
            if talla_data['talla'] == self.talla.talla:
                variante_id = talla_data.get('variante_id')
                if variante_id:
                    # Actualizar stock en Saleor
                    return saleor_service.actualizar_stock_variante(
                        variante_id, 
                        self.cantidad_disponible
                    )
        
        return False

    class Meta:
        unique_together = ('producto', 'talla')  # Evitar duplicados
        db_table = 'producto_talla'  # Nombre específico para la tabla

from django.contrib.auth.models import User

class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='favoritos')

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.nombre_pro}"
    
    class Meta:
        unique_together = ('usuario', 'producto')  # Evitar duplicados
        db_table = 'favorito'

