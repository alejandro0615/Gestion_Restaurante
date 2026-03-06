# Prototipo de fidelización para restaurante (Django)

Este proyecto implementa un prototipo funcional para fidelización de clientes con:

- Panel administrativo Django para gestionar carta, promociones, estrategias, clientes y pedidos.
- Sitio web público para consultar carta, buscar/filtrar productos y realizar pedidos.
- Mecanismo básico de puntos y redención de promociones.
- Descarga de carta en PDF.
- Registro de clientes con usuario/contraseña enviada por correo.
- Roles básicos: `admin` (panel Django) y `cliente` (pedidos y acumulación de puntos).

## Requisitos

- Python 3.13+
- Dependencias del archivo `requirements.txt`
- Node.js 18+ (para compilar Tailwind local)

## Instalación

1. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Ejecutar migraciones:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Crear usuario administrador:

   ```bash
   python manage.py createsuperuser
   ```

4. Iniciar servidor:

   ```bash
   python manage.py runserver
   ```

## Tailwind local (personalización)

Este proyecto usa Tailwind compilado localmente (no CDN) para permitir personalizaciones.

1. Instalar dependencias front:

   ```bash
   npm install
   ```

2. Compilar una vez:

   ```bash
   npm run tailwind:build
   ```

3. Modo desarrollo (recompila al guardar):

   ```bash
   npm run tailwind:watch
   ```

Archivos principales de Tailwind:

- Configuración: `tailwind.config.js`
- Entrada CSS: `static/src/tailwind.css`
- Salida compilada: `static/css/tailwind.css`

## Rutas clave

- Sitio público: `/`
- Registro cliente: `/registro/`
- Carta (filtros): `/carta/`
- Pedido: `/pedido/`
- Carta en PDF: `/carta/pdf/`
- Admin: `/admin/`

## Flujo recomendado de demo

1. Entrar al admin y crear categorías, productos, estrategias y promociones.
2. Registrar un cliente en `/registro/` e iniciar sesión con la contraseña recibida por correo.
3. Ir al sitio público y filtrar productos en la carta.
4. Realizar un pedido y aplicar una promoción (si hay puntos suficientes).
5. Ver confirmación de pedido con puntos ganados/redimidos.
6. Descargar la carta en PDF.

## Envío de códigos por Gmail

Para enviar correos reales (no solo consola), define estas variables de entorno antes de correr el servidor:

- `EMAIL_HOST_USER=tu_correo@gmail.com`
- `EMAIL_HOST_PASSWORD=tu_app_password`
- Opcionales: `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`

Luego en el admin:

1. Ve a `Clientes`.
2. Selecciona uno o varios clientes.
3. Ejecuta la acción **Generar y enviar código de compra por correo**.

Si no configuras esas variables, Django usará backend de consola (modo pruebas).
