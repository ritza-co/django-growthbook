from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='source',
            field=models.CharField(
                choices=[('storefront', 'Storefront'), ('internal', 'Internal')],
                default='internal',
                max_length=20,
            ),
        ),
    ]
