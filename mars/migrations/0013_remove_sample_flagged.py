# Generated by Django 3.1.4 on 2020-12-09 14:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mars', '0012_auto_20201208_1853'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sample',
            name='flagged',
        ),
    ]
