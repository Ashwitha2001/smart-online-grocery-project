# Generated by Django 4.2.12 on 2024-09-15 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0044_alter_customer_phone_number_alter_vendor_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
