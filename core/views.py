from decimal import Decimal  # Manejo preciso de dinero (sin errores de float).
from io import BytesIO  # Buffer en memoria para generar/retornar PDF.
import unicodedata  # Normalización de texto para PDF básico.

from django.contrib import messages  # Mensajes al usuario en templates.
from django.contrib.auth import get_user_model  # Modelo de usuario activo de Django.
from django.contrib.auth.models import Group  # Grupos para manejar roles básicos.
from django.core.mail import send_mail  # Utilidad para enviar correos.
from django.conf import settings  # Configuración del proyecto Django.
from django.db.models import Q  # Construcción de filtros OR en consultas.
from django.http import FileResponse  # Respuesta de descarga de archivos.
from django.shortcuts import redirect, render  # Helpers de respuesta web.
from django.urls import reverse  # Construye URLs por nombre de ruta.
from django.contrib.auth.decorators import login_required  # Protección de vistas.
from django.utils import timezone  # Fecha/hora con zona de Django.
from django.utils.crypto import get_random_string  # Generador seguro de códigos.

from .forms import (  # Formularios de entrada.
	CanjearCodigoClienteForm,
	ClienteRegistroForm,
	PedidoPublicoForm,
	ProductoMenuForm,
	RegistroClientePublicoForm,
	CambiarContraseñaForm,
)
from .services import asignar_regalo_por_puntos  # Regla central de regalo por superar 1.000 puntos.


PUNTOS_POR_PRODUCTO = 10  # Regla base: cada producto comprado otorga 10 puntos.
UMBRAL_COMPRA_PUNTOS_BONO = Decimal('20000')  # Umbral de total para activar puntos fijos por compra.
PUNTOS_BONO_COMPRA = 20  # Puntos por compra cuando supera el umbral.
from .models import (  # Modelos de negocio usados por las vistas.
	BeneficioCliente,
	Categoria,
	Cliente,
	CodigoFidelizacion,
	EstrategiaFidelizacion,
	ItemPedido,
	MenuDia,
	Pedido,
	Producto,
	Promocion,
)


DIAS_SEMANA = [
	('lunes', 'Lunes'),
	('martes', 'Martes'),
	('miercoles', 'Miércoles'),
	('jueves', 'Jueves'),
	('viernes', 'Viernes'),
	('sabado', 'Sábado'),
	('domingo', 'Domingo'),
]


def _dia_actual_slug():
	# Devuelve el slug del día actual según la zona horaria configurada en Django.
	return DIAS_SEMANA[timezone.localdate().weekday()][0]


def _productos_menu_por_dia(dia_semana):
	# Obtiene productos disponibles del menú activo para el día solicitado.
	menu = MenuDia.objects.filter(dia_semana=dia_semana, activa=True).first()
	if not menu:
		return Producto.objects.filter(disponible=True, disponible_todos_los_dias=True).select_related('categoria').distinct()
	ids_ocultos = set(menu.productos_ocultos.values_list('id', flat=True))
	ids_locales = set(menu.productos.filter(disponible=True).values_list('id', flat=True))
	ids_globales = set(Producto.objects.filter(disponible=True, disponible_todos_los_dias=True).values_list('id', flat=True))
	ids_visibles = (ids_locales | ids_globales) - ids_ocultos
	return Producto.objects.filter(id__in=ids_visibles).select_related('categoria').distinct().order_by('nombre')


def _username_disponible_desde_email(email):
	# Crea un username único basado en correo para evitar colisiones de autenticación.
	User = get_user_model()
	base = email.lower().strip()
	username = base
	contador = 1
	while User.objects.filter(username=username).exists():
		contador += 1
		username = f'{base}-{contador}'
	return username


@login_required
def registro_cliente(request):
	# Registro público: crea perfil Cliente + usuario con rol cliente y envía contraseña por correo.
	if request.user.is_authenticated:
		messages.info(request, 'Ya tienes sesión iniciada.')
		return redirect('inicio')

	if request.method == 'POST':
		form = RegistroClientePublicoForm(request.POST)
		if form.is_valid():
			nombre = form.cleaned_data['nombre'].strip()
			email = form.cleaned_data['email'].strip().lower()
			telefono=form.cleaned_data['telefono'].strip.lower()
			cliente_existente = Cliente.objects.filter(email=email).first()
			if cliente_existente and cliente_existente.user:
				messages.error(request, 'Este correo ya tiene cuenta. Inicia sesión con ese usuario.')
				return redirect('login')

			User = get_user_model()
			if User.objects.filter(email=email).exists() and not cliente_existente:
				messages.error(request, 'Este correo ya existe en el sistema. Usa otro correo o inicia sesión.')
				return redirect('login')

			password_temporal = get_random_string(length=10)
			username = _username_disponible_desde_email(email)

			usuario = User.objects.create_user(
				username=username,
				email=email,
				telefono=telefono,
				password=password_temporal,
				first_name=nombre,
			)

			rol_cliente, _ = Group.objects.get_or_create(name='cliente')
			usuario.groups.add(rol_cliente)

			if cliente_existente:
				cliente_existente.nombre = nombre
				cliente_existente.user = usuario
				cliente_existente.save()
			else:
				Cliente.objects.create(
					nombre=nombre,
					email=email,
					telefono=telefono,
					user=usuario,
				)

			try:
				send_mail(
    				subject='Credenciales de acceso - Restaurante',
    				message=(
        			f'Hola {nombre},\n\n'
        			'Se creó tu cuenta de cliente en la plataforma del restaurante Dulce Pecado.\n'
        			'Tus credenciales de acceso son: '
        			f'Usuario: {username}\n'
        			f'Contraseña temporal: {password_temporal}\n\n'
        			'Por seguridad, inicia sesión y cambia tu contraseña desde tu perfil.\n\n'
        			'Apreciamos tu fidelidad y esperamos que disfrutes de nuestros productos y promociones.\n'
        			'Restaurante Dulce Pecado\n'
   					),
    				from_email=os.environ.get('EMAIL_USER'),
    				recipient_list=[email],
    				fail_silently=False,
				)
				messages.success(request, 'Registro exitoso. Revisa tu correo Gmail para ver tu contraseña temporal.')
			except Exception:
				messages.warning(
					request,
					'La cuenta fue creada, pero no se pudo enviar el correo. Revisa configuración SMTP de Gmail en variables de entorno.',
				)

			return redirect('login')
	else:
		form = RegistroClientePublicoForm()

	return render(request, 'core/registro_cliente.html', {'form': form})


@login_required
def inicio(request):
	# Construye datos principales que ve el usuario en home.
	promociones = Promocion.objects.filter(activa=True)[:4]
	productos_destacados = Producto.objects.filter(disponible=True)[:6]
	estrategias = EstrategiaFidelizacion.objects.filter(activo=True)
	beneficio_regalo = None
	nuevos_pedidos_web = 0

	if request.user.is_staff:
		nuevos_pedidos_qs = Pedido.objects.filter(notificacion_staff_pendiente=True)
		total_nuevos = nuevos_pedidos_qs.count()
		nuevos_pedidos_web = total_nuevos
		if total_nuevos:
			nuevos_pedidos_qs.update(notificacion_staff_pendiente=False)

	if request.user.is_authenticated and not request.user.is_staff:
		cliente = getattr(request.user, 'cliente_profile', None)
		if cliente:
			beneficio_regalo = (
				BeneficioCliente.objects.filter(cliente=cliente, reclamado=False)
				.order_by('-otorgado_en')
				.first()
			)

	return render(
		request,
		'core/inicio.html',
		{
			'promociones': promociones,
			'productos_destacados': productos_destacados,
			'estrategias': estrategias,
			'beneficio_regalo': beneficio_regalo,
			'nuevos_pedidos_web': nuevos_pedidos_web,
		},
	)


@login_required
def listar_clientes(request):
	# Listado general de clientes con búsqueda y filtrado para staff.
	if not request.user.is_staff:
		messages.error(request, 'No tienes permisos para ver clientes.')
		return redirect('inicio')

	# Procesar acciones rápidas desde formulario inline.
	if request.method == 'POST':
		action_type = request.POST.get('action_type', 'update_puntos')

		if action_type == 'marcar_regalo_reclamado':
			cliente_id = request.POST.get('cliente_id')
			cliente = Cliente.objects.filter(id=cliente_id).first()
			if not cliente:
				messages.error(request, 'No se encontró el cliente para marcar el regalo.')
				return redirect('listar_clientes')

			beneficio_pendiente = (
				BeneficioCliente.objects.filter(
					cliente=cliente,
					reclamado=False,
				)
				.order_by('-otorgado_en')
				.first()
			)
			if not beneficio_pendiente:
				messages.warning(request, f'{cliente.nombre} no tiene regalo pendiente por reclamar.')
				return redirect('listar_clientes')

			beneficio_pendiente.reclamado = True
			beneficio_pendiente.reclamado_en = timezone.now()
			beneficio_pendiente.save(update_fields=['reclamado', 'reclamado_en'])
			messages.success(request, f'Regalo de {cliente.nombre} marcado como reclamado en caja.')
			return redirect('listar_clientes')

		if action_type == 'delete_cliente':
			cliente_id = request.POST.get('cliente_id')
			cliente = Cliente.objects.filter(id=cliente_id).first()
			if cliente:
				nombre_cliente = cliente.nombre
				usuario_vinculado = cliente.user
				cliente.delete()
				if usuario_vinculado:
					usuario_vinculado.delete()
				messages.success(request, f'Cliente {nombre_cliente} eliminado correctamente.')
			else:
				messages.error(request, 'No se encontró el cliente a eliminar.')
			return redirect('listar_clientes')

		cliente_id = request.POST.get('cliente_id')
		nuevos_puntos = request.POST.get('puntos', '')
		cliente = Cliente.objects.filter(id=cliente_id).first()
		if cliente and nuevos_puntos.isdigit():
			cliente.puntos = int(nuevos_puntos)
			cliente.save()
			regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)
			if regalo_asignado and correo_enviado:
				messages.success(request, f'Puntos de {cliente.nombre} actualizados. Se asignó regalo automático.')
			elif regalo_asignado:
				messages.success(request, f'Puntos de {cliente.nombre} actualizados. Se asignó regalo (correo falló).')
			else:
				messages.success(request, f'Puntos de {cliente.nombre} actualizados.')
		else:
			messages.error(request, 'Datos inválidos para actualizar puntos.')
		return redirect('listar_clientes')

	busqueda = request.GET.get('q', '').strip()
	clientes = Cliente.objects.all().order_by('-creado_en')

	if busqueda:
		clientes = clientes.filter(
			Q(nombre__icontains=busqueda)
			| Q(email__icontains=busqueda)
			| Q(cedula__icontains=busqueda)
			| Q(telefono__icontains=busqueda)
		)

	ids_clientes = list(clientes.values_list('id', flat=True))
	beneficios_regalo = BeneficioCliente.objects.filter(cliente_id__in=ids_clientes)
	regalos_pendientes_ids = set(beneficios_regalo.filter(reclamado=False).values_list('cliente_id', flat=True))
	regalos_reclamados_ids = set(beneficios_regalo.filter(reclamado=True).values_list('cliente_id', flat=True))

	return render(
		request,
		'core/listar_clientes_panel.html',
		{
			'clientes': clientes,
			'busqueda': busqueda,
			'total_clientes': Cliente.objects.count(),
			'regalos_pendientes_ids': regalos_pendientes_ids,
			'regalos_reclamados_ids': regalos_reclamados_ids,
		},
	)


@login_required
def registrar_cliente_panel(request):
	# Registro manual de clientes desde panel web de staff (fuera de /admin).
	# Crea un User automáticamente con usuario/contraseña y envía credenciales por correo.
	if not request.user.is_staff:
		messages.error(request, 'No tienes permisos para registrar clientes desde este panel.')
		return redirect('inicio')

	if request.method == 'POST':
		form = ClienteRegistroForm(request.POST)
		if form.is_valid():
			cliente = form.save(commit=False)
			
			# Genera username único basado en el email.
			User = get_user_model()
			username = _username_disponible_desde_email(cliente.email)
			
			# Genera contraseña segura aleatoria (8 caracteres).
			# Genera contraseña simple aleatoria (8 caracteres, solo letras y números).
			contraseña_temporal = get_random_string(length=8, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
			
			# Crea el User vinculado.
			user = User.objects.create_user(
				username=username,
				email=cliente.email,
				password=contraseña_temporal,
				first_name=cliente.nombre.split()[0] if cliente.nombre else '',
				last_name=' '.join(cliente.nombre.split()[1:]) if len(cliente.nombre.split()) > 1 else '',
			)
			
			# Asigna el User al Cliente y guarda.
			cliente.user = user
			cliente.save()
			
			# Envía correo con credenciales de acceso.
			try:
				send_mail(
					subject='Bienvenido a nuestro restaurante - Tus credenciales',
					message=(
						f'Hola {cliente.nombre},\n\n'
						f'Tu cuenta ha sido creada exitosamente en nuestro sistema.\n\n'
						f'Aquí están tus credenciales de acceso:\n'
						f'  Usuario: {username}\n'
						f'  Contraseña: {contraseña_temporal}\n\n'
						f'Con estas credenciales puedes acceder a tu perfil, ver tus puntos de fidelización y canjear códigos.\n\n'
						f'Por seguridad, te recomendamos cambiar tu contraseña la primera vez que inicies sesión.\n\n'
						f'¡Gracias por tu confianza!\n\n'
						f'Saludos,\nEquipo del Restaurante'
					),
					from_email=settings.DEFAULT_FROM_EMAIL,
					recipient_list=[cliente.email],
					fail_silently=False,
				)
				credentials_enviados = True
			except Exception as e:
				credentials_enviados = False
				print(f'Error al enviar correo de credenciales: {e}')
			
			# Verifica si se asigna regalo automático por 1000 puntos.
			regalo_asignado, correo_regalo_enviado = asignar_regalo_por_puntos(cliente)
			
			# Mensajes de éxito y estado del envío.
			messages.success(request, f'Cliente {cliente.nombre} registrado correctamente.')
			
			if credentials_enviados:
				messages.success(request, f'Se enviaron credenciales a {cliente.email}.')
			else:
				messages.warning(request, f'No se pudieron enviar las credenciales a {cliente.email}.')
			
			if regalo_asignado and correo_regalo_enviado:
				messages.success(request, f'Se asignó regalo automático y se envió notificación.')
			elif regalo_asignado:
				messages.warning(request, f'Se asignó regalo automático pero falló el correo de notificación.')
			
			return redirect('registrar_cliente_panel')
	else:
		form = ClienteRegistroForm()

	return render(request, 'core/registro_cliente_panel.html', {'form': form})


@login_required
def enviar_codigos_aleatorios(request):
	# Envía códigos de fidelización a 5 clientes aleatorios desde la vista principal (solo staff).
	if request.method != 'POST':
		return redirect('inicio')

	if not request.user.is_staff:
		messages.error(request, 'No tienes permisos para ejecutar este envío.')
		return redirect('inicio')

	clientes = list(Cliente.objects.exclude(email='').order_by('?')[:5])
	if not clientes:
		messages.warning(request, 'No hay clientes disponibles para enviar códigos.')
		return redirect('inicio')

	enviados = 0
	fallidos = 0
	for cliente in clientes:
		try:
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
			enviados += 1
		except Exception:
			fallidos += 1

	if enviados:
		messages.success(request, f'Se enviaron {enviados} código(s) a clientes aleatorios.')
	if fallidos:
		messages.error(request, f'Fallaron {fallidos} envío(s). Revisa la configuración SMTP.')

	return redirect('inicio')


def carta(request):
	# Lee filtros enviados por query string (/carta/?q=...&categoria=...).
	dia = request.GET.get('dia', _dia_actual_slug()).strip().lower() or _dia_actual_slug()
	dias_validos = {clave for clave, _ in DIAS_SEMANA}
	if dia not in dias_validos:
		dia = _dia_actual_slug()

	busqueda = request.GET.get('q', '').strip()
	categoria_id = request.GET.get('categoria', '').strip()
	productos = _productos_menu_por_dia(dia)

	if busqueda:
		# Filtra por nombre o descripción del producto.
		productos = productos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda))
	if categoria_id:
		# Filtra por categoría específica seleccionada.
		productos = productos.filter(categoria_id=categoria_id)

	categorias = Categoria.objects.filter(productos__in=productos).distinct().order_by('nombre')
	return render(
		request,
		'core/carta.html',
		{
			'productos': productos,
			'categorias': categorias,
			'busqueda': busqueda,
			'categoria_id': categoria_id,
			'dia': dia,
			'dias_semana': DIAS_SEMANA,
		},
	)

@login_required
def crear_pedido(request):
	# Vista de pedidos para clientes autenticados; usa el perfil vinculado para acumular puntos.
	cliente_autenticado = getattr(request.user, 'cliente_profile', None)
	if request.user.is_staff:
		cliente_autenticado = None
	elif not cliente_autenticado:
		messages.error(request, 'Debes registrarte como cliente antes de realizar pedidos.')
		return redirect('registro_cliente')

	dia = request.GET.get('dia', _dia_actual_slug()).strip().lower() or _dia_actual_slug()
	dias_validos = {clave for clave, _ in DIAS_SEMANA}
	if dia not in dias_validos:
		dia = _dia_actual_slug()

	if request.method == 'POST':
		dia_post = request.POST.get('dia', dia).strip().lower() or dia
		if dia_post in dias_validos:
			dia = dia_post

		datos = request.POST.copy()
		if cliente_autenticado:
			# Forza nombre/correo del perfil autenticado para evitar pedidos a otro cliente.
			datos['nombre'] = cliente_autenticado.nombre
			datos['email'] = cliente_autenticado.email

		form = PedidoPublicoForm(datos)
		# Restringe productos del pedido al menú activo del día.
		form.fields['productos'].queryset = _productos_menu_por_dia(dia)
		if form.is_valid():
			productos_disponibles = list(form.fields['productos'].queryset)
			productos_por_id = {str(producto.id): producto for producto in productos_disponibles}
			ids_marcados = set(request.POST.getlist('productos'))
			cantidades_por_producto = {}

			for producto_id, producto in productos_por_id.items():
				campo_cantidad = f'cantidad_{producto_id}'
				cantidad_raw = (request.POST.get(campo_cantidad) or '').strip()

				if not cantidad_raw:
					cantidad = 1 if producto_id in ids_marcados else 0
				elif cantidad_raw.isdigit():
					cantidad = int(cantidad_raw)
				else:
					form.add_error('productos', f'Cantidad inválida para {producto.nombre}. Usa solo números enteros.')
					continue

				if producto_id in ids_marcados and cantidad == 0:
					cantidad = 1

				if cantidad > 0:
					cantidades_por_producto[producto] = cantidad

			if not cantidades_por_producto:
				form.add_error('productos', 'Selecciona al menos un producto con cantidad mayor a 0.')

			if not form.errors:
				if cliente_autenticado:
					cliente = cliente_autenticado
					cliente.telefono = form.cleaned_data['telefono']
					cliente.save()
				else:
					email = form.cleaned_data['email']
					cliente, _ = Cliente.objects.get_or_create(
						email=email,
						defaults={
							'nombre': form.cleaned_data['nombre'],
							'telefono': form.cleaned_data['telefono'],
						},
					)

					cliente.nombre = form.cleaned_data['nombre']
					cliente.telefono = form.cleaned_data['telefono']
					cliente.save()

				total_unidades = sum(cantidades_por_producto.values())
				subtotal = sum(
					(producto.precio * cantidad for producto, cantidad in cantidades_por_producto.items()),
					Decimal('0.00'),
				)
				puntos_antes = cliente.puntos

				promocion = form.cleaned_data['promocion']
				descuento = Decimal('0.00')
				puntos_redimidos = 0
				beneficio_descuento = (
					BeneficioCliente.objects.filter(
						cliente=cliente,
						tipo='descuento_virtual',
						reclamado=False,
					)
					.order_by('-otorgado_en')
					.first()
				)
				usar_beneficio_virtual = request.POST.get('usar_beneficio_virtual') == 'on'
				beneficio_virtual_aplicado = False

				if usar_beneficio_virtual and beneficio_descuento and beneficio_descuento.descuento_porcentaje:
					descuento = (subtotal * Decimal(beneficio_descuento.descuento_porcentaje) / Decimal('100')).quantize(
						Decimal('0.01')
					)
					promocion = None
					beneficio_virtual_aplicado = True
				elif promocion and cliente.puntos >= promocion.puntos_requeridos:
					descuento = (subtotal * Decimal(promocion.descuento_porcentaje) / Decimal('100')).quantize(
						Decimal('0.01')
					)
					puntos_redimidos = promocion.puntos_requeridos
					cliente.puntos -= puntos_redimidos

				total = (subtotal - descuento).quantize(Decimal('0.01'))
				# Regla de fidelización: si el total supera 20.000, otorga 20 puntos por la compra.
				if total > UMBRAL_COMPRA_PUNTOS_BONO:
					puntos_ganados = PUNTOS_BONO_COMPRA
				else:
					puntos_ganados = total_unidades * PUNTOS_POR_PRODUCTO
				cliente.puntos += puntos_ganados
				cliente.save()
				regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)
				beneficio_nuevo = None
				if regalo_asignado:
					beneficio_nuevo = BeneficioCliente.objects.filter(cliente=cliente).order_by('-otorgado_en').first()
				if regalo_asignado and correo_enviado:
					if beneficio_nuevo and beneficio_nuevo.tipo == 'descuento_virtual':
						messages.success(
							request,
							f'🎁 ¡Felicidades! Ganaste un descuento virtual del {beneficio_nuevo.descuento_porcentaje}% para tu próximo pedido. Úsalo en Hacer pedido → Promoción.',
						)
					elif beneficio_nuevo and beneficio_nuevo.tipo == 'bebida_gratis':
						messages.success(
							request,
							'🎁 ¡Felicidades! Ganaste una bebida gratis. Reclámala en caja del restaurante con tu cédula o correo.',
						)
					else:
						messages.success(request, '🎁 ¡Felicidades! Se activó tu beneficio por superar 1.000 puntos. Revisa Inicio o Canjear códigos.')
				elif regalo_asignado:
					messages.warning(request, '🎁 Se activó tu beneficio por superar 1.000 puntos, aunque falló el envío de correo. Puedes verlo en Inicio o Canjear códigos.')
				elif puntos_antes < 1000 <= cliente.puntos:
					messages.info(request, '⭐ Ya superaste 1.000 puntos. Si ya tenías un beneficio asignado, puedes revisarlo en Inicio o Canjear códigos.')

				pedido = Pedido.objects.create(
					cliente=cliente,
					tipo_servicio=form.cleaned_data['tipo_servicio'],
					direccion_entrega=form.cleaned_data['direccion_entrega'],
					notas=form.cleaned_data['notas'],
					promocion_aplicada=promocion if descuento > 0 else None,
					subtotal=subtotal,
					descuento=descuento,
					total=total,
					puntos_ganados=puntos_ganados,
					puntos_redimidos=puntos_redimidos,
					notificacion_staff_pendiente=True,
				)

				for producto, cantidad in cantidades_por_producto.items():
					ItemPedido.objects.create(
						pedido=pedido,
						producto=producto,
						cantidad=cantidad,
						precio_unitario=producto.precio,
					)

				if beneficio_virtual_aplicado and beneficio_descuento:
					beneficio_descuento.reclamado = True
					beneficio_descuento.reclamado_en = timezone.now()
					beneficio_descuento.save(update_fields=['reclamado', 'reclamado_en'])
					messages.success(
						request,
						f'✅ Se aplicó tu beneficio virtual del {beneficio_descuento.descuento_porcentaje}% en este pedido.',
					)

				return redirect('pedido_exitoso', pedido_id=pedido.id)
	else:
		initial = {}
		if cliente_autenticado:
			# Precarga nombre/correo para cliente autenticado.
			initial = {'nombre': cliente_autenticado.nombre, 'email': cliente_autenticado.email}
		form = PedidoPublicoForm(initial=initial)
		form.fields['productos'].queryset = _productos_menu_por_dia(dia)

	productos_menu = list(form.fields['productos'].queryset)
	seleccionados = form['productos'].value() or []
	seleccionados = {str(valor) for valor in seleccionados}
	cantidades_seleccionadas = {}
	if request.method == 'POST':
		for producto in productos_menu:
			cantidad_raw = (request.POST.get(f'cantidad_{producto.id}') or '').strip()
			if cantidad_raw.isdigit() and int(cantidad_raw) > 0:
				cantidades_seleccionadas[str(producto.id)] = int(cantidad_raw)
	for producto_id in seleccionados:
		cantidades_seleccionadas.setdefault(producto_id, 1)
	seleccionados = seleccionados | set(cantidades_seleccionadas.keys())
	promociones_activas = Promocion.objects.filter(activa=True)
	beneficio_descuento_disponible = None
	beneficio_bebida_pendiente = None
	if cliente_autenticado:
		beneficio_descuento_disponible = (
			BeneficioCliente.objects.filter(
				cliente=cliente_autenticado,
				tipo='descuento_virtual',
				reclamado=False,
			)
			.order_by('-otorgado_en')
			.first()
		)
		beneficio_bebida_pendiente = (
			BeneficioCliente.objects.filter(
				cliente=cliente_autenticado,
				tipo='bebida_gratis',
				reclamado=False,
			)
			.order_by('-otorgado_en')
			.first()
		)
	return render(
		request,
		'core/pedido_form.html',
		{
			'form': form,
			'dia': dia,
			'dias_semana': DIAS_SEMANA,
			'productos_menu': productos_menu,
			'productos_seleccionados': seleccionados,
			'cantidades_seleccionadas': cantidades_seleccionadas,
			'promociones_activas': promociones_activas,
			'bloquear_identidad': bool(cliente_autenticado),
			'puntos_por_producto': PUNTOS_POR_PRODUCTO,
			'umbral_puntos_bono': UMBRAL_COMPRA_PUNTOS_BONO,
			'puntos_bono_compra': PUNTOS_BONO_COMPRA,
			'puntos_cliente_actuales': cliente_autenticado.puntos if cliente_autenticado else 0,
			'beneficio_descuento_disponible': beneficio_descuento_disponible,
			'beneficio_bebida_pendiente': beneficio_bebida_pendiente,
		},
	)


@login_required
def pedido_exitoso(request, pedido_id):
	# Muestra resumen del pedido recién creado.
	pedido = Pedido.objects.select_related('cliente', 'promocion_aplicada').prefetch_related('items__producto').get(id=pedido_id)
	return render(request, 'core/pedido_exitoso.html', {'pedido': pedido})


@login_required
def gestionar_pedidos(request):
	# Vista web para gestionar ventas sin entrar al panel admin.
	if not request.user.is_staff:
		messages.error(request, 'No tienes permisos para gestionar pedidos.')
		return redirect('inicio')

	if request.method == 'POST':
		pedido_id = request.POST.get('pedido_id')
		nuevo_estado = request.POST.get('estado')

		pedido = Pedido.objects.filter(id=pedido_id).first()
		if not pedido:
			messages.error(request, 'El pedido no existe.')
			return redirect('gestionar_pedidos')

		# Estado "listo" se guarda como "entregado" en el modelo actual.
		estado_permitido = {'pendiente', 'entregado'}
		if nuevo_estado not in estado_permitido:
			messages.error(request, 'Estado no permitido.')
			return redirect('gestionar_pedidos')

		pedido.estado = nuevo_estado
		pedido.save(update_fields=['estado'])
		messages.success(request, f'Pedido #{pedido.id} actualizado a {pedido.get_estado_display()}.')
		return redirect('gestionar_pedidos')

	filtro_estado = request.GET.get('estado', 'todos').strip().lower()

	pedidos = Pedido.objects.select_related('cliente').prefetch_related('items__producto')
	if filtro_estado == 'pendiente':
		pedidos = pedidos.filter(estado='pendiente')
	elif filtro_estado == 'listo':
		pedidos = pedidos.filter(estado='entregado')

	pedidos = pedidos.order_by('-creado_en')
	return render(
		request,
		'core/pedidos_gestion.html',
		{
			'pedidos': pedidos,
			'filtro_estado': filtro_estado,
		},
	)


@login_required
def gestionar_menus(request):
	# Vista operativa para gestionar menús por día sin usar el admin de Django.
	if not request.user.is_staff:
		messages.error(request, 'No tienes permisos para gestionar menús.')
		return redirect('inicio')

	dia = request.GET.get('dia', _dia_actual_slug()).strip().lower() or _dia_actual_slug()
	dias_validos = {clave for clave, _ in DIAS_SEMANA}
	if dia not in dias_validos:
		dia = _dia_actual_slug()

	menu, _ = MenuDia.objects.get_or_create(dia_semana=dia, defaults={'activa': True})
	q = request.GET.get('q', '').strip()
	producto_id = request.GET.get('producto_id', '').strip()
	producto_editar = Producto.objects.filter(id=producto_id).first() if producto_id.isdigit() else None
	producto_form = ProductoMenuForm(instance=producto_editar) if producto_editar else None
	ids_globales = set(Producto.objects.filter(disponible=True, disponible_todos_los_dias=True).values_list('id', flat=True))
	ids_locales = set(menu.productos.values_list('id', flat=True))
	ids_agregados = ids_locales | ids_globales
	productos_agregados = Producto.objects.filter(id__in=ids_agregados).select_related('categoria').order_by('nombre')
	ids_ocultos = set(menu.productos_ocultos.values_list('id', flat=True))

	productos_filtrados = Producto.objects.none()
	if q:
		productos_filtrados = (
			Producto.objects.filter(disponible=True)
			.exclude(id__in=ids_agregados)
			.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
			.select_related('categoria')
			.order_by('nombre')
		)

	if request.method == 'POST':
		action = request.POST.get('action', 'guardar_menu')
		dia_post = request.POST.get('dia', dia).strip().lower() or dia
		if dia_post in dias_validos:
			dia = dia_post
			menu, _ = MenuDia.objects.get_or_create(dia_semana=dia, defaults={'activa': True})

		if action == 'editar_producto':
			producto_id_post = request.POST.get('producto_id', '').strip()
			producto_obj = Producto.objects.filter(id=producto_id_post).first() if producto_id_post.isdigit() else None
			if not producto_obj:
				messages.error(request, 'Producto no encontrado para editar.')
				return redirect(f"{reverse('gestionar_menus')}?dia={dia}")

			producto_form = ProductoMenuForm(request.POST, instance=producto_obj)
			if producto_form.is_valid():
				producto_form.save()
				messages.success(request, f'Producto {producto_obj.nombre} actualizado correctamente.')
				return redirect(f"{reverse('gestionar_menus')}?dia={dia}&producto_id={producto_obj.id}")
			producto_editar = producto_obj
		else:
			menu.activa = request.POST.get('activa') == 'on'
			menu.save(update_fields=['activa'])

			ids_productos = {int(valor) for valor in request.POST.getlist('productos') if valor.isdigit()}

			productos_nuevos = Producto.objects.filter(id__in=ids_productos, disponible=True)
			if productos_nuevos.exists():
				menu.productos.add(*productos_nuevos)

			ids_agregados_actuales = set(menu.productos.values_list('id', flat=True)) | set(
				Producto.objects.filter(disponible=True, disponible_todos_los_dias=True).values_list('id', flat=True)
			)
			ids_visibles = ids_agregados_actuales.intersection(ids_productos)
			ids_ocultar = ids_agregados_actuales.difference(ids_visibles)
			menu.productos_ocultos.set(Producto.objects.filter(id__in=ids_ocultar))

			messages.success(request, f'Menú de {dict(DIAS_SEMANA).get(dia, dia)} actualizado correctamente.')
			url = f"{reverse('gestionar_menus')}?dia={dia}"
			if q:
				url += f"&q={q}"
			return redirect(url)

	seleccionados = ids_agregados.difference(ids_ocultos)

	return render(
		request,
		'core/menus_gestion.html',
		{
			'dia': dia,
			'dias_semana': DIAS_SEMANA,
			'q': q,
			'menu': menu,
			'productos_filtrados': productos_filtrados,
			'productos_seleccionados': seleccionados,
			'productos_ocultos': ids_ocultos,
			'productos_agregados': productos_agregados,
			'producto_editar': producto_editar,
			'producto_form': producto_form,
		},
	)


@login_required
def canjear_codigos(request):
	# Vista cliente: solo canje de código personal de un solo uso.
	cliente = getattr(request.user, 'cliente_profile', None)
	if not cliente:
		messages.error(request, 'Debes tener perfil de cliente para canjear códigos.')
		return redirect('inicio')

	if request.method == 'POST':
		canje_form = CanjearCodigoClienteForm(request.POST)
		if canje_form.is_valid():
			codigo_digitado = canje_form.cleaned_data['codigo'].strip().upper()

			codigo_cliente = CodigoFidelizacion.objects.filter(cliente=cliente, codigo=codigo_digitado).first()
			if not codigo_cliente:
				messages.error(request, 'El código no es válido para tu cuenta.')
				return redirect('canjear_codigos')

			if codigo_cliente.usado:
				messages.error(request, 'Este código ya fue utilizado anteriormente.')
				return redirect('canjear_codigos')

			codigo_cliente.usado = True
			codigo_cliente.usado_en = timezone.now()
			codigo_cliente.save(update_fields=['usado', 'usado_en'])

			cliente.puntos += 50
			puntos_antes = cliente.puntos - 50
			cliente.save(update_fields=['puntos'])
			regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)
			beneficio_nuevo = None
			if regalo_asignado:
				beneficio_nuevo = BeneficioCliente.objects.filter(cliente=cliente).order_by('-otorgado_en').first()
			messages.success(request, f'Código válido. Recibiste 50 puntos gratis. Total actual: {cliente.puntos}.')
			if regalo_asignado and correo_enviado:
				if beneficio_nuevo and beneficio_nuevo.tipo == 'descuento_virtual':
					messages.success(
						request,
						f'🎁 ¡Ganaste un descuento virtual del {beneficio_nuevo.descuento_porcentaje}% para tu próximo pedido! Úsalo en Hacer pedido → Promoción.',
					)
				elif beneficio_nuevo and beneficio_nuevo.tipo == 'bebida_gratis':
					messages.success(
						request,
						'🎁 ¡Ganaste una bebida gratis! Reclámala en caja del restaurante con tu cédula o correo.',
					)
				else:
					messages.success(request, '🎁 ¡Además superaste 1.000 puntos y se activó tu beneficio! Revisa Inicio o Canjear códigos.')
			elif regalo_asignado:
				messages.warning(request, '🎁 Se activó tu beneficio por superar 1.000 puntos, aunque falló el correo. Puedes verlo en Inicio o Canjear códigos.')
			elif puntos_antes < 1000 <= cliente.puntos:
				messages.info(request, '⭐ Ya superaste 1.000 puntos. Si ya tenías un beneficio asignado, puedes revisarlo en Inicio o Canjear códigos.')
			return redirect('canjear_codigos')
	else:
		canje_form = CanjearCodigoClienteForm()

	return render(
		request,
		'core/fidelizacion.html',
		{
			'canje_form': canje_form,
			'cliente': cliente,
			'beneficio_regalo': BeneficioCliente.objects.filter(cliente=cliente, reclamado=False).order_by('-otorgado_en').first(),
		},
	)


def _build_simple_pdf(lines):
	# Generador PDF mínimo sin dependencias externas (fallback).
	def normalize(texto):
		texto_ascii = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
		return texto_ascii

	def esc(texto):
		texto = normalize(texto)
		return texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

	text_commands = ['BT', '/F1 11 Tf', '14 TL', '50 760 Td']
	for index, line in enumerate(lines):
		if index == 0:
			text_commands.append(f'({esc(line)}) Tj')
		else:
			text_commands.append('T*')
			text_commands.append(f'({esc(line)}) Tj')
	text_commands.append('ET')

	stream = '\n'.join(text_commands).encode('latin-1', errors='replace')

	objects = []
	objects.append(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
	objects.append(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
	objects.append(
		b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n'
	)
	objects.append(
		b'4 0 obj\n<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream\nendobj\n'
	)
	objects.append(b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n')

	pdf = b'%PDF-1.4\n'
	offsets = [0]
	for obj in objects:
		offsets.append(len(pdf))
		pdf += obj

	xref_pos = len(pdf)
	pdf += b'xref\n0 6\n'
	pdf += b'0000000000 65535 f \n'
	for offset in offsets[1:]:
		pdf += f'{offset:010d} 00000 n \n'.encode('ascii')

	pdf += b'trailer\n<< /Size 6 /Root 1 0 R >>\n'
	pdf += b'startxref\n' + str(xref_pos).encode('ascii') + b'\n%%EOF'
	return pdf


def descargar_carta_pdf(request):
	# Prepara líneas de la carta a exportar.
	dia_param = request.GET.get('dia', _dia_actual_slug()).strip().lower() or _dia_actual_slug()
	dias_validos = [clave for clave, _ in DIAS_SEMANA]
	nombres_dias = dict(DIAS_SEMANA)

	if dia_param == 'todos':
		dias_a_exportar = dias_validos
	elif dia_param in dias_validos:
		dias_a_exportar = [dia_param]
	else:
		dias_a_exportar = [_dia_actual_slug()]

	lineas = ['Carta del Restaurante', '']
	for dia in dias_a_exportar:
		nombre_dia = nombres_dias.get(dia, dia.title())
		lineas.append(f'Menú del día: {nombre_dia}')
		productos = _productos_menu_por_dia(dia)
		if not productos.exists():
			lineas.append('No hay productos disponibles para este día.')
		else:
			for producto in productos:
				categoria = producto.categoria.nombre if producto.categoria else 'Sin categoría'
				lineas.append(f'{producto.nombre} ({categoria}) - ${producto.precio}')
		lineas.append('')

	try:
		# Camino principal: PDF con reportlab.
		from reportlab.lib import colors
		from reportlab.lib.pagesizes import letter
		from reportlab.pdfgen import canvas

		buffer = BytesIO()
		pdf = canvas.Canvas(buffer, pagesize=letter)
		ancho, alto = letter

		titulo_pdf = (
			'Carta del Restaurante - Semana'
			if len(dias_a_exportar) > 1
			else f"Carta del Restaurante - {nombres_dias.get(dias_a_exportar[0], dias_a_exportar[0].title())}"
		)
		pdf.setTitle(titulo_pdf)

		def dibujar_encabezado(nombre_dia_local):
			pdf.setFillColor(colors.HexColor('#1D4ED8'))
			pdf.rect(0, alto - 110, ancho, 110, fill=1, stroke=0)
			pdf.setFillColor(colors.white)
			pdf.setFont('Helvetica-Bold', 22)
			pdf.drawString(42, alto - 58, 'Carta del Restaurante')
			pdf.setFont('Helvetica', 12)
			pdf.drawString(42, alto - 82, f'Menú del día: {nombre_dia_local}')
			fecha_actual = timezone.localdate().strftime('%d/%m/%Y')
			pdf.setFillColor(colors.HexColor('#334155'))
			pdf.setFont('Helvetica', 10)
			pdf.drawRightString(ancho - 42, alto - 122, f'Generado: {fecha_actual}')
			pdf.setFillColor(colors.HexColor('#0F172A'))
			pdf.setFont('Helvetica-Bold', 13)
			pdf.drawString(42, alto - 150, 'Platos disponibles')

		def dibujar_pie():
			pdf.setFillColor(colors.HexColor('#94A3B8'))
			pdf.setFont('Helvetica', 8)
			pdf.drawCentredString(ancho / 2, 26, 'Gracias por preferirnos · Restaurante ADSO')

		for indice, dia in enumerate(dias_a_exportar):
			nombre_dia = nombres_dias.get(dia, dia.title())
			productos = _productos_menu_por_dia(dia)

			if indice > 0:
				pdf.showPage()

			dibujar_encabezado(nombre_dia)
			y = alto - 168

			if not productos.exists():
				pdf.setFont('Helvetica', 11)
				pdf.setFillColor(colors.HexColor('#475569'))
				pdf.drawString(42, y, 'No hay productos disponibles para este día.')
				dibujar_pie()
				continue

			for producto in productos:
				if y < 110:
					dibujar_pie()
					pdf.showPage()
					dibujar_encabezado(nombre_dia)
					y = alto - 168

				altura_tarjeta = 52
				pdf.setFillColor(colors.HexColor('#F8FAFC'))
				pdf.roundRect(36, y - altura_tarjeta + 10, ancho - 72, altura_tarjeta, 8, fill=1, stroke=0)

				pdf.setFillColor(colors.HexColor('#0F172A'))
				pdf.setFont('Helvetica-Bold', 11)
				pdf.drawString(48, y + 2, producto.nombre[:55])

				categoria = producto.categoria.nombre if producto.categoria else 'Sin categoría'
				pdf.setFillColor(colors.HexColor('#475569'))
				pdf.setFont('Helvetica', 9)
				pdf.drawString(48, y - 12, f'Categoría: {categoria}')

				precio = f'${producto.precio}'
				pdf.setFillColor(colors.HexColor('#047857'))
				pdf.setFont('Helvetica-Bold', 11)
				pdf.drawRightString(ancho - 48, y + 2, precio)

				descripcion = (producto.descripcion or 'Delicioso plato del día.').strip()
				descripcion = descripcion[:95] + '...' if len(descripcion) > 95 else descripcion
				pdf.setFillColor(colors.HexColor('#334155'))
				pdf.setFont('Helvetica', 9)
				pdf.drawString(48, y - 26, descripcion)

				y -= 62

			dibujar_pie()

		pdf.save()
		buffer.seek(0)
		return FileResponse(buffer, as_attachment=True, filename='carta_restaurante.pdf')
	except ModuleNotFoundError:
		# Fallback: PDF simple si reportlab no está instalado.
		pdf_bytes = _build_simple_pdf(lineas)
		return FileResponse(BytesIO(pdf_bytes), as_attachment=True, filename='carta_restaurante.pdf')



@login_required
def cambiar_contraseña(request):
	# Vista para que el cliente autenticado pueda cambiar su contraseña.
	
	if request.method == 'POST':
		form = CambiarContraseñaForm(request.POST)
		if form.is_valid():
			# Valida que la contraseña actual sea correcta.
			if not request.user.check_password(form.cleaned_data['contraseña_actual']):
				messages.error(request, 'La contraseña actual es incorrecta.')
				return render(request, 'core/cambiar_contraseña.html', {'form': form})
			
			# Actualiza la contraseña a la nueva.
			new_password = form.cleaned_data['contraseña_nueva']
			request.user.set_password(new_password)
			request.user.save()
			
			# Redirige a login para que el usuario inicie sesión con la nueva contraseña.
			messages.success(request, 'Tu contraseña ha sido cambiada correctamente. Por favor, inicia sesión nuevamente.')
			return redirect('login')
	else:
		form = CambiarContraseñaForm()
	
	return render(request, 'core/cambiar_contraseña.html', {'form': form})
