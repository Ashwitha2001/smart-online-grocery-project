# Generated by Django 5.1.1 on 2024-10-05 12:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0077_deliverypersonnel_assigned_orders_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cart',
            unique_together={('customer', 'product')},
        ),
    ]
