# Generated by Django 5.1.1 on 2024-10-04 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0070_admin'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=255)),
                ('units_sold', models.IntegerField()),
                ('total_sales', models.DecimalField(decimal_places=2, max_digits=10)),
                ('sale_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
