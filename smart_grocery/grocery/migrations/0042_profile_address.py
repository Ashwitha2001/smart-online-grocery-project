# Generated by Django 4.2.12 on 2024-09-14 07:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0041_alter_vendor_email_alter_vendor_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
    ]
