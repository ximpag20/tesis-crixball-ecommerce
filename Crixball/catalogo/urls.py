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
    path("carrito/checkout/", views.checkout_view, name="checkout"),
    path("carrito/actualizar-cantidad/", views.carrito_actualizar_cantidad, name="carrito_actualizar_cantidad"),
    path('carrito/procesar-pago/', views.procesar_pago_checkout, name='procesar_pago'),  # 🔥 NUEVO
    path("carrito/braintree-token/", views.braintree_token, name="braintree_token"),
    path("comprobante/", views.ver_comprobante, name="ver_comprobante"),
    path("comprobante/pdf/", views.descargar_comprobante_pdf, name="comprobante_pdf"),
    path("mis-comprobantes/", views.mis_comprobantes, name="mis_comprobantes"),
    path("mis-comprobantes/<int:id_comprobante>/", views.detalle_comprobante, name="detalle_comprobante"),
    path(     "comprobante/<int:id_comprobante>/pdf/",     views.descargar_comprobante_pdf_bd,     name="comprobante_pdf_bd" ), 

]