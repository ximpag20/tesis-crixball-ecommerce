from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Catalogo, name='Catalogo'),
    path('administrar/', views.administrar_productos, name='administrar_productos'),
    path('producto/<int:producto_id>/', views.DetallesProducto, name='detalles_producto'),
    path('favorito/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('actualizar-producto/<int:id_pro>/', views.actualizar_producto, name='actualizar_producto'),
]