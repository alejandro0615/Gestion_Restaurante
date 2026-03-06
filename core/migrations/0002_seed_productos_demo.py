from django.db import migrations


def seed_productos_demo(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    Producto = apps.get_model('core', 'Producto')

    categorias = {
        'Entradas': [
            ('Nachos mixtos', 'Totopos con queso fundido, guacamole y pico de gallo.', '18000.00'),
            ('Alitas BBQ', 'Alitas de pollo bañadas en salsa BBQ.', '22000.00'),
        ],
        'Platos fuertes': [
            ('Hamburguesa clásica', 'Carne artesanal, queso cheddar, lechuga y tomate.', '28000.00'),
            ('Pizza pepperoni', 'Pizza mediana con pepperoni y mozzarella.', '36000.00'),
            ('Pasta boloñesa', 'Pasta al dente con salsa boloñesa casera.', '30000.00'),
        ],
        'Bebidas': [
            ('Limonada natural', 'Limonada fresca endulzada al gusto.', '9000.00'),
            ('Gaseosa', 'Bebida gaseosa personal.', '7000.00'),
            ('Jugo de mango', 'Jugo natural de mango en agua o leche.', '11000.00'),
        ],
        'Postres': [
            ('Brownie con helado', 'Brownie tibio con bola de helado de vainilla.', '15000.00'),
            ('Cheesecake de frutos rojos', 'Porción de cheesecake con cobertura de frutos rojos.', '16000.00'),
        ],
    }

    for nombre_categoria, productos in categorias.items():
        categoria, _ = Categoria.objects.get_or_create(nombre=nombre_categoria)
        for nombre, descripcion, precio in productos:
            Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'categoria': categoria,
                    'descripcion': descripcion,
                    'precio': precio,
                    'disponible': True,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_productos_demo, migrations.RunPython.noop),
    ]
