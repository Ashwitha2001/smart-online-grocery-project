# Generated by Django 4.2.12 on 2024-09-11 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0020_order_total_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
