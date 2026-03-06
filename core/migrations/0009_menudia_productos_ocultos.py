from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_agregar_productos_especiales'),
    ]

    operations = [
        migrations.AddField(
            model_name='menudia',
            name='productos_ocultos',
            field=models.ManyToManyField(blank=True, related_name='menus_dia_ocultos', to='core.producto'),
        ),
    ]
