# Generated by Django 3.1.4 on 2020-12-08 04:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mars', '0010_auto_20201207_2022'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='library',
            options={'ordering': ['name'], 'verbose_name_plural': 'Libraries'},
        ),
    ]
