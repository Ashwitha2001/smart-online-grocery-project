# Generated by Django 4.2.12 on 2024-09-19 06:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0049_remove_profile_email'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='email',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='email',
        ),
    ]
