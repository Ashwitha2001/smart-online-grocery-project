# Generated by Django 4.2.12 on 2024-09-19 10:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0051_rename_delivery_personnel_delivery_delivery_partner_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='delivery_personnel',
            new_name='delivery_partner',
        ),
    ]
