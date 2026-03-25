from django.test import TestCase, Client
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from unittest.mock import patch
from core.models import Cliente
from core.models import (
    BeneficioCliente,
    CodigoFidelizacion,
    Pedido,
    Producto,
    Promocion,
)
from core.forms import (
    CambiarContraseñaForm,
    ClienteRegistroForm,
    PedidoPublicoForm,
    RegistroClientePublicoForm,
)
from core.services import asignar_regalo_por_puntos
from core.admin import ClienteAdmin

User = get_user_model()


class InicioViewTest(TestCase):

    def setUp(self):
        """Prepara un cliente HTTP y un usuario base para pruebas de inicio."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='12345678'
        )

    def test_redirige_si_no_logueado(self):
        """Verifica que la vista inicio requiera autenticación."""
        response = self.client.get(reverse('inicio'))
        self.assertEqual(response.status_code, 302)

    def test_acceso_logueado(self):
        """Verifica que un usuario autenticado pueda abrir inicio."""
        self.client.login(username='testuser', password='12345678')
        response = self.client.get(reverse('inicio'))
        self.assertEqual(response.status_code, 200)
        
class RegistroClienteTest(TestCase):

    def setUp(self):
        """Configura cliente HTTP y usuario auxiliar para el módulo de registro."""
        self.client = Client()
        self.user = User.objects.create_user(
        username='test',
        password='12345678'
    )

    def test_registro_cliente_valido(self):
        """Comprueba que staff pueda registrar un cliente desde el panel."""
    # Crear usuario admin
        admin = User.objects.create_user(
            username='admin',
            password='12345678',
            is_staff=True  # IMPORTANTE
        )

        # Loguearlo
        self.client.login(username='admin', password='12345678')

        # Hacer la petición
        response = self.client.post(reverse('registrar_cliente_panel'), {
            'nombre': 'Juan Perez',
            'cedula': '123456789',
            'email': 'juan@test.com',
            'telefono': '123456789',
        })
        print(response.context)
        # Verificar redirección (éxito)
        self.assertEqual(response.status_code, 302)

        # Verificar que se creó
        self.assertTrue(
            Cliente.objects.filter(email='juan@test.com').exists()
        )
        
class ListarClientesTest(TestCase):

    def setUp(self):
        """Crea usuarios staff y no staff para validar permisos de listado."""
        self.client = Client()

        self.user_normal = User.objects.create_user(
            username='normal',
            password='12345678'
        )

        self.user_staff = User.objects.create_user(
            username='admin',
            password='12345678',
            is_staff=True
        )

    def test_usuario_no_staff_no_accede(self):
        """Valida que usuario normal sea redirigido al intentar listar clientes."""
        self.client.login(username='normal', password='12345678')
        response = self.client.get(reverse('listar_clientes'))
        self.assertEqual(response.status_code, 302)

    def test_usuario_staff_accede(self):
        """Valida que usuario staff sí tenga acceso al listado de clientes."""
        self.client.login(username='admin', password='12345678')
        response = self.client.get(reverse('listar_clientes'))
        self.assertEqual(response.status_code, 200)
        
class CrearPedidoTest(TestCase):

    def setUp(self):
        """Prepara un cliente autenticable con un producto disponible para pedir."""
        self.client = Client()

        self.user = User.objects.create_user(
            username='cliente',
            password='12345678'
        )

        self.cliente = Cliente.objects.create(
            user=self.user,
            nombre='Cliente Test',
            email='cliente@test.com',
            telefono='123'
        )

        self.producto = Producto.objects.create(
            nombre='Pizza',
            precio=10000,
            disponible=True,
            disponible_todos_los_dias=True
        )

    def test_crear_pedido(self):
        """Verifica que el flujo básico de creación de pedido termine en redirección."""
        self.client.login(username='cliente', password='12345678')

        data = {
            'nombre': 'Cliente Test',
            'email': 'cliente@test.com',
            'telefono': '123',
            'productos': [self.producto.id],
            f'cantidad_{self.producto.id}': '1',
            'tipo_servicio': 'domicilio',
            'direccion_entrega': 'Calle 123 #45-67',
        }

        response = self.client.post(reverse('crear_pedido'), data)
        print(response.context)  # 👈 DEBUG

        self.assertEqual(response.status_code, 302)
        
        
class CambiarPasswordTest(TestCase):

    def setUp(self):
        """Prepara usuario autenticable para probar el cambio de contraseña."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='test',
            password='12345678'
        )

    def test_cambiar_password(self):
        """Valida que el endpoint cambie contraseña y redirija a login."""
        self.client.login(username='test', password='12345678')

        data = {
            'contraseña_actual': '12345678',
            'contraseña_nueva': 'nueva12345',
            'contraseña_nueva_confirmacion': 'nueva12345'
        }

        response = self.client.post(reverse('cambiar_contraseña'), data)
        print(response.status_code)
        print(response.url) 

        self.assertEqual(response.status_code, 302)

        # Verifica que cambió
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('nueva12345'))


class ServicesTest(TestCase):

    @patch('core.services.random.choice')
    @patch('core.services.send_mail')
    def test_asignar_regalo_descuento_virtual(self, send_mail_mock, choice_mock):
        """Confirma asignación de descuento virtual, reinicio de puntos y envío de correo."""
        user = User.objects.create_user(username='serv1', password='12345678')
        cliente = Cliente.objects.create(
            user=user,
            nombre='Cliente Servicio',
            email='servicio@test.com',
            telefono='111',
            puntos=1000,
        )
        choice_mock.side_effect = ['descuento_virtual', 25]

        regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)

        self.assertTrue(regalo_asignado)
        self.assertTrue(correo_enviado)
        cliente.refresh_from_db()
        self.assertEqual(cliente.puntos, 0)
        beneficio = BeneficioCliente.objects.get(cliente=cliente)
        self.assertEqual(beneficio.tipo, 'descuento_virtual')
        self.assertEqual(beneficio.descuento_porcentaje, 25)
        send_mail_mock.assert_called_once()

    @patch('core.services.random.choice')
    @patch('core.services.send_mail', side_effect=Exception('smtp down'))
    def test_asignar_regalo_con_fallo_correo(self, _send_mail_mock, choice_mock):
        """Confirma que el beneficio se asigne aunque falle el correo SMTP."""
        user = User.objects.create_user(username='serv2', password='12345678')
        cliente = Cliente.objects.create(
            user=user,
            nombre='Cliente Servicio 2',
            email='servicio2@test.com',
            telefono='222',
            puntos=1400,
        )
        choice_mock.side_effect = ['bebida_gratis']

        regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)

        self.assertTrue(regalo_asignado)
        self.assertFalse(correo_enviado)
        cliente.refresh_from_db()
        self.assertEqual(cliente.puntos, 0)
        beneficio = BeneficioCliente.objects.get(cliente=cliente)
        self.assertEqual(beneficio.tipo, 'bebida_gratis')

    def test_asignar_regalo_no_aplica_por_puntos_bajos(self):
        """Valida que con menos de 1000 puntos no se cree ningún beneficio."""
        user = User.objects.create_user(username='serv3', password='12345678')
        cliente = Cliente.objects.create(
            user=user,
            nombre='Cliente Bajo',
            email='bajo@test.com',
            telefono='333',
            puntos=999,
        )

        regalo_asignado, correo_enviado = asignar_regalo_por_puntos(cliente)

        self.assertFalse(regalo_asignado)
        self.assertFalse(correo_enviado)
        self.assertFalse(BeneficioCliente.objects.filter(cliente=cliente).exists())


class FormsTest(TestCase):

    def test_pedido_publico_form_requiere_direccion_en_domicilio(self):
        """Comprueba que domicilio sin dirección sea inválido."""
        form = PedidoPublicoForm(data={
            'nombre': 'Ana',
            'email': 'ana@test.com',
            'telefono': '123',
            'tipo_servicio': 'domicilio',
            'direccion_entrega': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('direccion_entrega', form.errors)

    def test_pedido_publico_form_sitio_limpia_direccion(self):
        """Comprueba que en servicio en sitio se limpie dirección enviada."""
        form = PedidoPublicoForm(data={
            'nombre': 'Ana',
            'email': 'ana2@test.com',
            'telefono': '123',
            'tipo_servicio': 'sitio',
            'direccion_entrega': 'Calle 123 #45-67',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['direccion_entrega'], '')

    def test_cliente_registro_form_detecta_duplicados(self):
        """Valida duplicados de email, cédula y teléfono en registro de cliente."""
        user = User.objects.create_user(
            username='maildup',
            password='12345678',
            email='duplicado@test.com',
        )
        Cliente.objects.create(
            user=user,
            nombre='Existente',
            email='existente@test.com',
            telefono='999',
            cedula='9001',
        )

        form = ClienteRegistroForm(data={
            'nombre': 'Nuevo',
            'cedula': '9001',
            'telefono': '999',
            'email': 'duplicado@test.com',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('cedula', form.errors)
        self.assertIn('telefono', form.errors)

    def test_registro_publico_form_email_duplicado(self):
        """Verifica bloqueo de email ya existente en registro público."""
        Cliente.objects.create(
            nombre='Existente',
            email='publico@test.com',
            telefono='555',
            cedula='8001',
        )
        form = RegistroClientePublicoForm(data={
            'nombre': 'Nuevo',
            'email': 'publico@test.com',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_cambiar_contrasena_form_no_coincide(self):
        """Asegura que el formulario invalide contraseñas nuevas distintas."""
        form = CambiarContraseñaForm(data={
            'contraseña_actual': '12345678',
            'contraseña_nueva': 'nueva1234',
            'contraseña_nueva_confirmacion': 'diferente1234',
        })
        self.assertFalse(form.is_valid())


class ViewsExtraTest(TestCase):

    def setUp(self):
        """Crea datos base para pruebas de vistas de staff y cliente."""
        self.client = Client()
        self.staff = User.objects.create_user(username='staffx', password='12345678', is_staff=True)
        self.user_cliente = User.objects.create_user(username='clientex', password='12345678')
        self.cliente = Cliente.objects.create(
            user=self.user_cliente,
            nombre='Cliente Vista',
            email='clientevista@test.com',
            telefono='300',
            cedula='7001',
            puntos=300,
        )
        self.producto = Producto.objects.create(
            nombre='Hamburguesa',
            precio=10000,
            disponible=True,
            disponible_todos_los_dias=True,
        )

    def test_inicio_staff_limpia_notificacion_pendiente(self):
        """Verifica que al entrar staff se limpien notificaciones pendientes."""
        Pedido.objects.create(
            cliente=self.cliente,
            tipo_servicio='sitio',
            subtotal=10000,
            descuento=0,
            total=10000,
            notificacion_staff_pendiente=True,
        )
        self.client.login(username='staffx', password='12345678')

        response = self.client.get(reverse('inicio'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Pedido.objects.filter(notificacion_staff_pendiente=True).exists())

    def test_listar_clientes_marcar_regalo_reclamado(self):
        """Valida acción de staff para marcar regalo como reclamado."""
        self.client.login(username='staffx', password='12345678')
        beneficio = BeneficioCliente.objects.create(
            cliente=self.cliente,
            tipo='bebida_gratis',
            descripcion='Bebida gratis',
            reclamado=False,
        )

        response = self.client.post(reverse('listar_clientes'), {
            'action_type': 'marcar_regalo_reclamado',
            'cliente_id': self.cliente.id,
        })

        self.assertEqual(response.status_code, 302)
        beneficio.refresh_from_db()
        self.assertTrue(beneficio.reclamado)

    def test_listar_clientes_delete_cliente(self):
        """Valida eliminación de cliente y de su usuario vinculado desde panel."""
        self.client.login(username='staffx', password='12345678')
        user_id = self.user_cliente.id

        response = self.client.post(reverse('listar_clientes'), {
            'action_type': 'delete_cliente',
            'cliente_id': self.cliente.id,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cliente.objects.filter(id=self.cliente.id).exists())
        self.assertFalse(User.objects.filter(id=user_id).exists())

    @patch('core.views.send_mail')
    def test_enviar_codigos_aleatorios_staff(self, send_mail_mock):
        """Comprueba envío masivo de códigos aleatorios por usuario staff."""
        Cliente.objects.create(nombre='C2', email='c2@test.com', telefono='1', cedula='7002')
        self.client.login(username='staffx', password='12345678')

        response = self.client.post(reverse('enviar_codigos_aleatorios'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(CodigoFidelizacion.objects.count() >= 1)
        self.assertTrue(send_mail_mock.called)

    @patch('core.views.asignar_regalo_por_puntos', return_value=(False, False))
    def test_canjear_codigo_valido(self, _asignar_mock):
        """Verifica canje válido: marca código usado y suma 50 puntos."""
        self.client.login(username='clientex', password='12345678')
        codigo = CodigoFidelizacion.objects.create(cliente=self.cliente, codigo='AB12CD34')
        puntos_antes = self.cliente.puntos

        response = self.client.post(reverse('canjear_codigos'), {
            'codigo': 'AB12CD34',
        })

        self.assertEqual(response.status_code, 302)
        codigo.refresh_from_db()
        self.cliente.refresh_from_db()
        self.assertTrue(codigo.usado)
        self.assertEqual(self.cliente.puntos, puntos_antes + 50)

    def test_canjear_codigo_invalido_para_otro_cliente(self):
        """Verifica que un cliente no pueda canjear códigos de otra cuenta."""
        otro = Cliente.objects.create(nombre='Otro', email='otro@test.com', telefono='22', cedula='7003')
        CodigoFidelizacion.objects.create(cliente=otro, codigo='ZX12CV34')
        self.client.login(username='clientex', password='12345678')

        response = self.client.post(reverse('canjear_codigos'), {
            'codigo': 'ZX12CV34',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(CodigoFidelizacion.objects.get(codigo='ZX12CV34').usado)

    @patch('core.views.asignar_regalo_por_puntos', return_value=(False, False))
    def test_crear_pedido_con_promocion(self, _asignar_mock):
        """Valida cálculo de subtotal, descuento y puntos redimidos con promoción."""
        promocion = Promocion.objects.create(
            titulo='Promo50',
            descripcion='Mitad de precio',
            descuento_porcentaje=50,
            puntos_requeridos=100,
            activa=True,
        )
        self.client.login(username='clientex', password='12345678')

        response = self.client.post(reverse('crear_pedido'), {
            'nombre': self.cliente.nombre,
            'email': self.cliente.email,
            'telefono': self.cliente.telefono,
            'tipo_servicio': 'domicilio',
            'direccion_entrega': 'Calle 123 #45-67',
            'productos': [self.producto.id],
            f'cantidad_{self.producto.id}': '2',
            'promocion': promocion.id,
        })

        self.assertEqual(response.status_code, 302)
        pedido = Pedido.objects.latest('id')
        self.assertEqual(pedido.subtotal, 20000)
        self.assertEqual(pedido.descuento, 10000)
        self.assertEqual(pedido.total, 10000)
        self.assertEqual(pedido.puntos_redimidos, 100)

    def test_crear_pedido_usuario_sin_perfil_cliente(self):
        """Comprueba redirección a registro cuando usuario no tiene perfil Cliente."""
        user_sin_perfil = User.objects.create_user(username='sinperfil', password='12345678')
        self.client.login(username='sinperfil', password='12345678')

        response = self.client.get(reverse('crear_pedido'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('registro_cliente'), response.url)

    def test_descargar_carta_pdf_responde_archivo(self):
        """Valida que la descarga de carta retorne archivo PDF."""
        response = self.client.get(reverse('descargar_carta_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('carta_restaurante.pdf', response.get('Content-Disposition', ''))


class AdminClienteTest(TestCase):

    def setUp(self):
        """Inicializa RequestFactory y modelo admin para pruebas unitarias de admin."""
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin_obj = ClienteAdmin(Cliente, self.site)
        self.staff = User.objects.create_user(username='adminuser', password='12345678', is_staff=True)
        self.cliente = Cliente.objects.create(
            nombre='Cliente Admin',
            email='clienteadmin@test.com',
            telefono='555',
            cedula='6001',
        )

    def test_permiso_modelo_cliente_admin_bloqueado(self):
        """Verifica que Cliente esté oculto y bloqueado en módulo admin."""
        request = self.factory.get('/admin/')
        request.user = self.staff
        self.assertFalse(self.admin_obj.has_module_permission(request))
        self.assertFalse(self.admin_obj.has_view_permission(request))
        self.assertFalse(self.admin_obj.has_add_permission(request))
        self.assertFalse(self.admin_obj.has_change_permission(request))
        self.assertFalse(self.admin_obj.has_delete_permission(request))

    @patch('core.admin.send_mail')
    @patch('core.admin.get_random_string', return_value='AB12CD34')
    def test_generar_y_enviar_codigo_crea_codigo(self, _random_mock, send_mail_mock):
        """Comprueba generación de código y envío de correo desde admin."""
        self.admin_obj._generar_y_enviar_codigo(self.cliente)
        self.assertTrue(CodigoFidelizacion.objects.filter(cliente=self.cliente, codigo='AB12CD34').exists())
        send_mail_mock.assert_called_once()

    def test_enviar_codigo_individual_cliente_no_existe(self):
        """Valida respuesta controlada al intentar enviar código a cliente inexistente."""
        request = self.factory.get('/admin/core/cliente/999/enviar-codigo/')
        request.user = self.staff

        with patch.object(self.admin_obj, 'message_user') as message_user_mock:
            response = self.admin_obj.enviar_codigo_individual(request, 999)

        self.assertEqual(response.status_code, 302)
        message_user_mock.assert_called()

    @patch.object(ClienteAdmin, '_generar_y_enviar_codigo')
    def test_enviar_codigo_individual_exitoso(self, generar_mock):
        """Valida flujo exitoso de envío individual de código en admin."""
        request = self.factory.get(f'/admin/core/cliente/{self.cliente.id}/enviar-codigo/')
        request.user = self.staff

        with patch.object(self.admin_obj, 'message_user') as message_user_mock:
            response = self.admin_obj.enviar_codigo_individual(request, self.cliente.id)

        self.assertEqual(response.status_code, 302)
        generar_mock.assert_called_once()
        message_user_mock.assert_called()