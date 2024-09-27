# Generated by Django 4.2.12 on 2024-09-19 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0050_remove_customer_email_remove_vendor_email'),
    ]

    operations = [
        migrations.RenameField(
            model_name='delivery',
            old_name='delivery_personnel',
            new_name='delivery_partner',
        ),
        migrations.AddField(
            model_name='delivery',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
