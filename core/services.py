import random

from django.core.mail import send_mail  # Envío de correos desde configuración SMTP de Django.

from .models import BeneficioCliente  # Registro de beneficios entregados a clientes.


def asignar_regalo_por_puntos(cliente):
	# Otorga regalo una sola vez cuando el cliente alcanza o supera 1.000 puntos.
	if cliente.puntos < 1000:
		return False, False  # No aplica regalo todavía.

	# Premio aleatorio: descuento virtual (10%-75%) o bebida gratis presencial.
	tipo_beneficio = random.choice(['descuento_virtual', 'bebida_gratis'])
	descuento_porcentaje = None
	if tipo_beneficio == 'descuento_virtual':
		descuento_porcentaje = random.choice(list(range(10, 80, 5)))
		descripcion_regalo = f'Descuento virtual del {descuento_porcentaje}% en tu próximo pedido'
	else:
		descripcion_regalo = 'Bebida gratis (reclamo presencial en caja)'

	BeneficioCliente.objects.create(
		cliente=cliente,
		tipo=tipo_beneficio,
		descuento_porcentaje=descuento_porcentaje,
		descripcion=descripcion_regalo,
	)

	# Reinicia el contador al alcanzar/superar el límite de puntos.
	cliente.puntos = 0
	cliente.save(update_fields=['puntos'])

	try:
		send_mail(
			subject='¡Tienes un regalo por fidelidad!',
			message=(
				f'Hola {cliente.nombre},\n\n'
				'¡Felicitaciones! Superaste los 1.000 puntos de fidelización.\n'
				f'Te asignamos este beneficio: {descripcion_regalo}.\n\n'
				'Puedes verlo en tu inicio y en la sección de canjear códigos.\n\n'
				'Gracias por preferirnos.\n'
				'Restaurante Dulce Pecado'
			),
			from_email=None,
			recipient_list=[cliente.email],
			fail_silently=False,
		)
		return True, True
	except Exception:
		# Si falla SMTP, el regalo queda asignado y luego puede notificarse manualmente.
		return True, False
