# Generated by Django 4.2.12 on 2024-09-13 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0028_alter_subcategory_table'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
