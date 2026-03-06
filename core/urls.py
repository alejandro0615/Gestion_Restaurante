from django.urls import path  # Helper de Django para declarar rutas.

from . import views  # Vistas locales de la app core.

urlpatterns = [
    path('', views.inicio, name='inicio'),  # Home pública.
    path('enviar-codigos-aleatorios/', views.enviar_codigos_aleatorios, name='enviar_codigos_aleatorios'),  # Envío staff de códigos a 5 clientes aleatorios.
    path('panel/clientes/', views.listar_clientes, name='listar_clientes'),  # Listado de clientes para staff.
    path('panel/clientes/registrar/', views.registrar_cliente_panel, name='registrar_cliente_panel'),  # Registro de clientes desde panel web de staff.
    path('registro/', views.registro_cliente, name='registro_cliente'),  # Registro de cliente con credenciales por correo.
    path('carta/', views.carta, name='carta'),  # Vista de catálogo con filtros.
    path('pedido/', views.crear_pedido, name='crear_pedido'),  # Creación de pedido con acumulación de puntos.
    path('pedido/exitoso/<int:pedido_id>/', views.pedido_exitoso, name='pedido_exitoso'),  # Confirmación del pedido creado.
    path('pedidos/', views.gestionar_pedidos, name='gestionar_pedidos'),  # Gestión de pedidos para staff fuera de admin.
    path('menus/', views.gestionar_menus, name='gestionar_menus'),  # Gestión de menús por día para staff fuera de admin.
    path('canjear-codigos/', views.canjear_codigos, name='canjear_codigos'),  # Registro y canje de códigos.
    path('carta/pdf/', views.descargar_carta_pdf, name='descargar_carta_pdf'),  # Descarga carta en PDF.

    path('cambiar-contraseña/', views.cambiar_contraseña, name='cambiar_contraseña'),  # Cambio de contraseña para clientes autenticados.
]

