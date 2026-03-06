from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_alter_beneficiocliente_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='notificacion_staff_pendiente',
            field=models.BooleanField(default=False),
        ),
    ]
