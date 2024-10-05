# Generated by Django 5.1.1 on 2024-09-30 09:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0061_alter_order_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='status',
            field=models.CharField(choices=[('Placed', 'Placed'), ('Processing', 'Processing'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Canceled', 'Canceled')], default='Pending', max_length=20),
        ),
    ]
