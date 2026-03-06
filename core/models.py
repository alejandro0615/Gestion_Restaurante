from django.db import models  # ORM de Django para definir tablas y relaciones.
from django.conf import settings  # Referencia al modelo de usuario configurado en Django.


class Categoria(models.Model):
	nombre = models.CharField(max_length=80, unique=True)  # Nombre único de categoría en la carta.

	class Meta:
		verbose_name = 'Categoría'  # Nombre singular en admin Django.
		verbose_name_plural = 'Categorías'  # Nombre plural en admin Django.
		ordering = ['nombre']  # Orden alfabético por defecto.

	def __str__(self):
		return self.nombre  # Texto legible del objeto en admin/listas.


class Producto(models.Model):
	categoria = models.ForeignKey(  # Relación muchos-a-uno con categoría.
		Categoria,
		on_delete=models.SET_NULL,  # Si borran categoría, producto queda sin categoría.
		null=True,  # Permite NULL en base de datos.
		blank=True,  # Permite vacío en formularios.
		related_name='productos',  # Acceso inverso: categoria.productos.
	)
	nombre = models.CharField(max_length=120)  # Nombre comercial del producto.
	descripcion = models.TextField(blank=True)  # Descripción opcional para cliente.
	precio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio con 2 decimales.
	disponible = models.BooleanField(default=True)  # Controla visibilidad en carta.
	disponible_todos_los_dias = models.BooleanField(default=False)  # Si está activo, aparece en todos los menús diarios.

	class Meta:
		ordering = ['nombre']  # Muestra productos ordenados por nombre.

	def __str__(self):
		return f'{self.nombre} - ${self.precio}'  # Etiqueta legible del producto.


class EstrategiaFidelizacion(models.Model):
	nombre = models.CharField(max_length=120)  # Nombre interno de la estrategia.
	descripcion = models.TextField()  # Explica regla de fidelización.
	activo = models.BooleanField(default=True)  # Indica si se usa actualmente.
	puntos_por_mil = models.PositiveIntegerField(default=1)  # Puntos por cada 1000 de compra.
	codigos_para_beneficio = models.PositiveIntegerField(default=5)  # Meta de códigos para premio.

	class Meta:
		verbose_name = 'Estrategia de fidelización'  # Etiqueta singular en admin.
		verbose_name_plural = 'Estrategias de fidelización'  # Etiqueta plural en admin.

	def __str__(self):
		estado = 'Activa' if self.activo else 'Inactiva'  # Texto de estado legible.
		return f'{self.nombre} ({estado})'  # Representación final de la estrategia.


class Cliente(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='cliente_profile',
	)  # Relación opcional con usuario autenticable del sistema.
	nombre = models.CharField(max_length=120)  # Nombre completo del cliente.
	cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Documento único.
	email = models.EmailField(unique=True)  # Correo único para contacto/códigos.
	telefono = models.CharField(max_length=30, blank=True)  # Teléfono de contacto.
	puntos = models.PositiveIntegerField(default=0)  # Acumulado de fidelización.
	creado_en = models.DateTimeField(auto_now_add=True)  # Fecha de creación automática.

	class Meta:
		ordering = ['-creado_en']  # Clientes más recientes primero.

	def __str__(self):
		return f'{self.nombre} - {self.email}'  # Texto visible en admin/listas.


class Promocion(models.Model):
	titulo = models.CharField(max_length=140)  # Nombre de la promoción.
	descripcion = models.TextField()  # Detalle para el cliente.
	descuento_porcentaje = models.PositiveIntegerField(default=0)  # Porcentaje de descuento.
	puntos_requeridos = models.PositiveIntegerField(default=0)  # Puntos necesarios para redimir.
	activa = models.BooleanField(default=True)  # Habilita/deshabilita su uso.
	fecha_inicio = models.DateField(null=True, blank=True)  # Inicio de vigencia opcional.
	fecha_fin = models.DateField(null=True, blank=True)  # Fin de vigencia opcional.

	class Meta:
		ordering = ['-id']  # Muestra primero las promociones recientes.

	def __str__(self):
		return self.titulo  # Texto legible de la promoción.


class Pedido(models.Model):
	TIPO_SERVICIO = (  # Opciones permitidas por Django para este campo.
		('sitio', 'Consumo en el sitio'),
		('domicilio', 'Entrega a domicilio'),
	)

	ESTADO = (  # Estados del ciclo de vida del pedido.
		('pendiente', 'Pendiente'),
		('en_preparacion', 'En preparación'),
		('entregado', 'Entregado'),
		('cancelado', 'Cancelado'),
	)

	cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos')  # Pedido pertenece a cliente.
	tipo_servicio = models.CharField(max_length=12, choices=TIPO_SERVICIO)  # Sitio o domicilio.
	direccion_entrega = models.CharField(max_length=250, blank=True)  # Dirección si aplica domicilio.
	notas = models.TextField(blank=True)  # Indicaciones adicionales.
	promocion_aplicada = models.ForeignKey(  # Promoción usada en el pedido (si hubo).
		Promocion,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='pedidos',
	)
	subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # Valor sin descuentos.
	descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Valor descontado.
	total = models.DecimalField(max_digits=10, decimal_places=2)  # Total final cobrado.
	puntos_ganados = models.PositiveIntegerField(default=0)  # Puntos otorgados por compra.
	puntos_redimidos = models.PositiveIntegerField(default=0)  # Puntos gastados en beneficios.
	estado = models.CharField(max_length=20, choices=ESTADO, default='pendiente')  # Estado actual del pedido.
	notificacion_staff_pendiente = models.BooleanField(default=False)  # Permite avisar una vez en panel de pedidos web cuando llega un pedido nuevo.
	creado_en = models.DateTimeField(auto_now_add=True)  # Fecha de creación del pedido.

	class Meta:
		ordering = ['-creado_en']  # Pedidos recientes primero.

	def __str__(self):
		return f'Pedido #{self.id} - {self.cliente.nombre}'  # Texto visible del pedido.


class ItemPedido(models.Model):
	pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')  # Ítem ligado a pedido.
	producto = models.ForeignKey(Producto, on_delete=models.PROTECT)  # Producto vendido en el ítem.
	cantidad = models.PositiveIntegerField(default=1)  # Cantidad del producto.
	precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)  # Precio unitario histórico.

	def __str__(self):
		return f'{self.cantidad} x {self.producto.nombre}'  # Resumen legible del ítem.


class CodigoFidelizacion(models.Model):
	cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='codigos')  # Código asignado a cliente.
	codigo = models.CharField(max_length=16, unique=True)  # Token único enviado por correo.
	usado = models.BooleanField(default=False)  # Marca si ya fue canjeado.
	creado_en = models.DateTimeField(auto_now_add=True)  # Fecha de generación.
	usado_en = models.DateTimeField(null=True, blank=True)  # Fecha de canje (si aplica).

	class Meta:
		ordering = ['-creado_en']  # Códigos nuevos primero.

	def __str__(self):
		estado = 'usado' if self.usado else 'pendiente'  # Estado legible del código.
		return f'{self.codigo} - {self.cliente.nombre} ({estado})'  # Texto en admin.


class BeneficioCliente(models.Model):
	TIPO_BENEFICIO = (  # Catálogo de premios posibles.
		('descuento_virtual', 'Descuento virtual'),
		('descuento_50', '50% de descuento'),
		('regalo_misterioso', 'Regalo misterioso'),
		('bebida_gratis', 'Bebida gratis'),
	)

	cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='beneficios')  # Beneficio entregado al cliente.
	tipo = models.CharField(max_length=20, choices=TIPO_BENEFICIO)  # Tipo estandarizado de premio.
	descuento_porcentaje = models.PositiveIntegerField(null=True, blank=True)  # Porcentaje para premios virtuales (10%-75%).
	descripcion = models.CharField(max_length=120)  # Texto mostrado al usuario.
	otorgado_en = models.DateTimeField(auto_now_add=True)  # Fecha de otorgamiento.
	reclamado = models.BooleanField(default=False)  # Indica si el cliente ya reclamó el beneficio en caja.
	reclamado_en = models.DateTimeField(null=True, blank=True)  # Momento en que el staff marcó el beneficio como reclamado.

	class Meta:
		ordering = ['-otorgado_en']  # Beneficios recientes primero.

	def __str__(self):
		return f'{self.cliente.nombre} - {self.get_tipo_display()}'  # Texto legible en panel admin.


class MenuDia(models.Model):
	DIA_SEMANA = (
		('lunes', 'Lunes'),
		('martes', 'Martes'),
		('miercoles', 'Miércoles'),
		('jueves', 'Jueves'),
		('viernes', 'Viernes'),
		('sabado', 'Sábado'),
		('domingo', 'Domingo'),
	)

	dia_semana = models.CharField(max_length=12, choices=DIA_SEMANA, unique=True)  # Día único al que aplica este menú.
	productos = models.ManyToManyField(Producto, related_name='menus_dia', blank=True)  # Productos disponibles para ese día.
	productos_ocultos = models.ManyToManyField(
		Producto,
		related_name='menus_dia_ocultos',
		blank=True,
	)  # Productos agregados al día pero ocultos para la carta/pedido del cliente.
	activa = models.BooleanField(default=True)  # Permite activar/desactivar el menú del día.

	class Meta:
		verbose_name = 'Menú por día'
		verbose_name_plural = 'Menús por día'
		ordering = ['dia_semana']

	def __str__(self):
		return dict(self.DIA_SEMANA).get(self.dia_semana, self.dia_semana)
