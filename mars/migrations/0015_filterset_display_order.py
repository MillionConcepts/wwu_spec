# Generated by Django 3.1.4 on 2020-12-10 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mars', '0014_sample_released'),
    ]

    operations = [
        migrations.AddField(
            model_name='filterset',
            name='display_order',
            field=models.IntegerField(blank=True, default=10000),
        ),
    ]
