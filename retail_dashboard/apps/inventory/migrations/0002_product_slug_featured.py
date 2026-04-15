from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    for product in Product.objects.all():
        base = slugify(product.name)
        slug = base
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        product.slug = slug
        product.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, unique=False, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='is_featured',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, unique=True),
        ),
    ]
