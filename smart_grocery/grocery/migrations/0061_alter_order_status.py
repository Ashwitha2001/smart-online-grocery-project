# Generated by Django 5.1.1 on 2024-09-27 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0060_alter_review_customer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('Placed', 'Placed'), ('Processing', 'Processing'), ('Shipped', 'Shipped'), ('Out for Delivery', 'Out for Delivery'), ('Delivered', 'Delivered'), ('Canceled', 'Canceled')], default='Placed', max_length=20),
        ),
    ]
