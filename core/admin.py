from django.contrib import admin  # Panel administrativo de Django.
from django.contrib import messages  # Mensajes flash en acciones admin.
from django import forms  # Formularios para personalizar validaciones en admin.
from django.core.mail import send_mail  # Utilidad de envío de correo de Django.
from django.http import HttpResponseRedirect  # Redirección tras acciones personalizadas en admin.
from django.urls import path, reverse  # Rutas personalizadas y generación de URLs en admin.
from django.utils.html import format_html  # Render seguro de botón HTML en columnas del admin.
from django.utils.crypto import get_random_string  # Generador de códigos aleatorios seguros.
from .services import asignar_regalo_por_puntos  # Regla central para regalo al superar 1.000 puntos.
from .models import (  # Modelos locales administrados desde /admin.
    BeneficioCliente,
	Categoria,
	CodigoFidelizacion,
	Cliente,
	EstrategiaFidelizacion,
	ItemPedido,
	MenuDia,
	Pedido,
	Producto,
	Promocion,
)


class ClienteAdminForm(forms.ModelForm):
	# Formulario admin para forzar captura de datos clave del cliente.
	class Meta:
		model = Cliente
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['nombre'].required = True
		self.fields['email'].required = True
		self.fields['telefono'].required = True
		self.fields['cedula'].required = True


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
	search_fields = ('nombre',)  # Permite buscar categorías por nombre.


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'categoria', 'precio', 'disponible')  # Columnas visibles del listado.
	list_filter = ('disponible', 'categoria')  # Filtros laterales en admin.
	search_fields = ('nombre', 'descripcion')  # Caja de búsqueda.


@admin.register(MenuDia)
class MenuDiaAdmin(admin.ModelAdmin):
	list_display = ('get_dia_semana_display', 'activa', 'cantidad_productos')  # Menú por día con total de productos configurados.
	list_filter = ('activa', 'dia_semana')  # Filtra menús activos e identifica el día.
	filter_horizontal = ('productos',)  # Selección cómoda de productos para la carta del día.
	search_fields = ('dia_semana', 'productos__nombre')  # Permite encontrar rápido el menú o productos asociados.
	list_editable = ('activa',)  # Activa/desactiva menú del día desde el listado.

	@admin.display(description='Productos del día')
	def cantidad_productos(self, obj):
		return obj.productos.count()  # Muestra cuántos productos tiene asignado cada menú diario.


@admin.register(EstrategiaFidelizacion)
class EstrategiaFidelizacionAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'puntos_por_mil', 'codigos_para_beneficio', 'activo')  # Campos relevantes de estrategia.
	list_filter = ('activo',)  # Filtra activas/inactivas.
	search_fields = ('nombre', 'descripcion')  # Busca por texto.


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
	form = ClienteAdminForm
	list_display = ('nombre', 'email', 'user', 'cedula', 'telefono', 'puntos', 'boton_enviar_codigo', 'creado_en')  # Resumen de cliente.
	search_fields = ('nombre', 'cedula', 'email', 'telefono', 'user__username')  # Busca cliente por datos clave.
	actions = ('enviar_codigo_por_correo',)  # Acción masiva personalizada.
	actions_selection_counter = True  # Muestra contador de seleccionados para enviar códigos a varios clientes.
	readonly_fields = ('creado_en',)
	fieldsets = (
		('Datos del cliente', {'fields': ('nombre', 'email', 'telefono', 'cedula')}),
		('Control de fidelización', {'fields': ('puntos', 'user')}),
		('Trazabilidad', {'fields': ('creado_en',)}),
	)

	def has_module_permission(self, request):
		# Oculta por completo el modelo Cliente del panel admin.
		return False

	def has_view_permission(self, request, obj=None):
		# Bloquea acceso a listado/detalle incluso por URL directa.
		return False

	def has_add_permission(self, request):
		# El registro de clientes se traslada al panel web staff (fuera de /admin).
		return False

	def has_change_permission(self, request, obj=None):
		# Bloquea edición desde admin; se gestiona en panel web normal.
		return False

	def has_delete_permission(self, request, obj=None):
		# Bloquea eliminación desde admin; se gestiona fuera del admin.
		return False

	def get_urls(self):
		# Agrega URL personalizada para enviar código individual desde el listado.
		urls = super().get_urls()
		custom_urls = [
			path(
				'<int:cliente_id>/enviar-codigo/',
				self.admin_site.admin_view(self.enviar_codigo_individual),
				name='core_cliente_enviar_codigo',
			),
		]
		return custom_urls + urls

	@admin.display(description='Enviar código')
	def boton_enviar_codigo(self, obj):
		# Botón rápido por cliente para generar y enviar código aleatorio al correo.
		url = reverse('admin:core_cliente_enviar_codigo', args=[obj.pk])
		return format_html(
			'<a class="button" href="{}" style="padding:6px 10px; border-radius:6px; background:#2563eb; color:#fff; text-decoration:none;">Enviar código</a>',
			url,
		)

	def _generar_y_enviar_codigo(self, cliente):
		# Lógica única para crear código aleatorio y enviarlo por correo al cliente.
		codigo = get_random_string(length=8, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')
		CodigoFidelizacion.objects.create(cliente=cliente, codigo=codigo)
		send_mail(
			subject='Tu código de fidelización',
			message=(
				f'Hola {cliente.nombre},\n\n'
				f'Tu código de compra es: {codigo}\n'
				'Ingresa este código en la sección Canjear códigos para sumar puntos.\n\n'
				'Restaurante'
			),
			from_email=None,
			recipient_list=[cliente.email],
			fail_silently=False,
		)

	def enviar_codigo_individual(self, request, cliente_id):
		# Endpoint admin para disparar envío individual desde botón del listado.
		cliente = Cliente.objects.filter(pk=cliente_id).first()
		if not cliente:
			self.message_user(request, 'Cliente no encontrado.', level=messages.ERROR)
			return HttpResponseRedirect('../')

		try:
			self._generar_y_enviar_codigo(cliente)
			self.message_user(request, f'Se envió un código a {cliente.nombre}.', level=messages.SUCCESS)
		except Exception:
			self.message_user(request, f'Falló el envío para {cliente.nombre}. Revisa configuración SMTP.', level=messages.ERROR)

		return HttpResponseRedirect('../')

	def save_model(self, request, obj, form, change):
		# Guarda el cliente y crea regalo automático cuando alcance 1000 puntos.
		super().save_model(request, obj, form, change)
		regalo_asignado, correo_enviado = asignar_regalo_por_puntos(obj)
		if regalo_asignado and correo_enviado:
			self.message_user(request, f'Se asignó regalo automático a {obj.nombre} y se notificó por correo.', level=messages.SUCCESS)
		elif regalo_asignado:
			self.message_user(request, f'Se asignó regalo automático a {obj.nombre}, pero falló el correo.', level=messages.WARNING)

	@admin.action(description='Generar y enviar código de compra por correo')
	def enviar_codigo_por_correo(self, request, queryset):
		enviados = 0  # Contador de códigos enviados en esta ejecución.
		fallidos = 0  # Contador de errores de envío.
		for cliente in queryset:
			try:
				self._generar_y_enviar_codigo(cliente)
				enviados += 1
			except Exception:
				fallidos += 1

		if enviados:
			self.message_user(request, f'Se enviaron {enviados} código(s) correctamente.', level=messages.SUCCESS)  # Feedback admin.
		if fallidos:
			self.message_user(request, f'Fallaron {fallidos} envío(s). Revisa configuración SMTP.', level=messages.ERROR)


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'descuento_porcentaje', 'puntos_requeridos', 'activa')  # Campos claves de promo.
	list_filter = ('activa',)  # Filtro por estado.
	search_fields = ('titulo', 'descripcion')  # Búsqueda por texto.


class ItemPedidoInline(admin.TabularInline):
	model = ItemPedido  # Ítems editables dentro del pedido.
	extra = 1  # Filas extra vacías al crear.


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
	list_display = ('id', 'cliente', 'tipo_servicio', 'total', 'puntos_ganados', 'estado', 'creado_en')  # Resumen de pedido.
	list_filter = ('tipo_servicio', 'estado', 'creado_en')  # Filtros útiles del listado.
	search_fields = ('cliente__nombre', 'cliente__email')  # Búsqueda por cliente.
	inlines = [ItemPedidoInline]  # Muestra ítems dentro del pedido.
	ordering = ('estado', '-creado_en')  # Muestra primero pedidos pendientes para generar venta.


@admin.register(CodigoFidelizacion)
class CodigoFidelizacionAdmin(admin.ModelAdmin):
	list_display = ('codigo', 'cliente', 'usado', 'creado_en', 'usado_en')  # Estado y trazabilidad del código.
	list_filter = ('usado', 'creado_en')  # Filtra usados/no usados.
	search_fields = ('codigo', 'cliente__nombre', 'cliente__cedula', 'cliente__email')  # Localiza por código o cliente.


@admin.register(BeneficioCliente)
class BeneficioClienteAdmin(admin.ModelAdmin):
	list_display = ('cliente', 'tipo', 'descripcion', 'otorgado_en')  # Historial de beneficios.
	list_filter = ('tipo', 'otorgado_en')  # Filtra por tipo/fecha.
	search_fields = ('cliente__nombre', 'cliente__cedula', 'cliente__email', 'descripcion')  # Búsqueda flexible.
