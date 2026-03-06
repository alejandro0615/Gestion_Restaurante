from decimal import Decimal

from django.db import migrations


def crear_productos_especiales(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    Producto = apps.get_model('core', 'Producto')

    categoria, _ = Categoria.objects.get_or_create(nombre='Especiales')

    productos = [
        ('Alitas BBQ', 'Porción de alitas bañadas en salsa BBQ, con papas a la francesa.', Decimal('22000.00')),
        ('Alitas Picantes', 'Alitas en salsa picante de la casa, acompañadas de bastones de zanahoria.', Decimal('22000.00')),
        ('Nachos Supremos', 'Nachos con queso fundido, carne desmechada, guacamole y pico de gallo.', Decimal('21000.00')),
        ('Hamburguesa Doble Queso', 'Pan brioche, doble carne, queso cheddar, tomate, lechuga y salsa especial.', Decimal('24000.00')),
        ('Costillas BBQ', 'Costillas de cerdo en salsa BBQ con papa rústica y ensalada fresca.', Decimal('28000.00')),
        ('Wrap de Pollo Crispy', 'Tortilla de trigo con pollo crispy, vegetales, queso y aderezo ranch.', Decimal('20000.00')),
        ('Combo Tacos Mixtos', 'Tres tacos surtidos de pollo, res y cerdo con salsas artesanales.', Decimal('23000.00')),
        ('Quesadilla Mexicana', 'Quesadilla de queso mozzarella con pollo salteado y maíz dulce.', Decimal('19500.00')),
    ]

    for nombre, descripcion, precio in productos:
        Producto.objects.get_or_create(
            nombre=nombre,
            defaults={
                'descripcion': descripcion,
                'precio': precio,
                'categoria': categoria,
                'disponible': True,
            },
        )


def eliminar_productos_especiales(apps, schema_editor):
    Producto = apps.get_model('core', 'Producto')
    nombres = [
        'Alitas BBQ',
        'Alitas Picantes',
        'Nachos Supremos',
        'Hamburguesa Doble Queso',
        'Costillas BBQ',
        'Wrap de Pollo Crispy',
        'Combo Tacos Mixtos',
        'Quesadilla Mexicana',
    ]
    Producto.objects.filter(nombre__in=nombres).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_mejorar_descripcion_platos'),
    ]

    operations = [
        migrations.RunPython(crear_productos_especiales, eliminar_productos_especiales),
    ]
