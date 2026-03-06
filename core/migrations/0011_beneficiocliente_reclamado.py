from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_producto_todos_los_dias'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiocliente',
            name='reclamado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='beneficiocliente',
            name='reclamado_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
