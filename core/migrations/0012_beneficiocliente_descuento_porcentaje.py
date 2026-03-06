from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_beneficiocliente_reclamado'),
    ]

    operations = [
        migrations.AddField(
            model_name='beneficiocliente',
            name='descuento_porcentaje',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
