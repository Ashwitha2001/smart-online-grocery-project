# Generated by Django 5.1.1 on 2024-09-30 12:57

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0064_order_ordered_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='ordered_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
