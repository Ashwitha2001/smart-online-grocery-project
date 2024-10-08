# Generated by Django 4.2.12 on 2024-09-12 07:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grocery', '0021_profile_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_date', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed'), ('Failed', 'Failed')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('delivery_personnel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveries', to='grocery.profile')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='grocery.order')),
            ],
        ),
    ]
