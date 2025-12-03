from django.urls import path
from . import views

urlpatterns = [
    path ('', views.Catalogo, name='Catalogo'),
    path('administrar/', views.administrar_productos, name='administrar_productos'),
    path('producto/<int:producto_id>/', views.DetallesProducto, name='detalles_producto'),
    path('favorito/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('actualizar-producto/<int:id_pro>/', views.actualizar_producto, name='actualizar_producto'),
    path("carrito/", views.ver_carrito, name="ver_carrito"),
    path("carrito/agregar/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/eliminar/<str:line_id>/", views.carrito_eliminar, name="carrito_eliminar"),
    path("carrito/", views.ver_carrito, name="ver_carrito"),

]