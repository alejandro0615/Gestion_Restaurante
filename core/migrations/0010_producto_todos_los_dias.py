from django.db import migrations, models



def marcar_productos_globales(apps, schema_editor):
    Producto = apps.get_model('core', 'Producto')
    Categoria = apps.get_model('core', 'Categoria')

    categoria_especiales = Categoria.objects.filter(nombre__iexact='Especiales').first()

    if categoria_especiales:
        Producto.objects.filter(categoria=categoria_especiales).update(disponible_todos_los_dias=True)

    Producto.objects.filter(nombre__icontains='alitas').update(disponible_todos_los_dias=True)



def desmarcar_productos_globales(apps, schema_editor):
    Producto = apps.get_model('core', 'Producto')
    Categoria = apps.get_model('core', 'Categoria')

    categoria_especiales = Categoria.objects.filter(nombre__iexact='Especiales').first()

    if categoria_especiales:
        Producto.objects.filter(categoria=categoria_especiales).update(disponible_todos_los_dias=False)

    Producto.objects.filter(nombre__icontains='alitas').update(disponible_todos_los_dias=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_menudia_productos_ocultos'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='disponible_todos_los_dias',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(marcar_productos_globales, desmarcar_productos_globales),
    ]
