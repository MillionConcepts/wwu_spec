# Generated by Django 3.1.4 on 2020-12-11 18:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mars', '0017_auto_20201211_1824'),
    ]

    operations = [
        migrations.RenameField(
            model_name='filterset',
            old_name='name',
            new_name='short_name',
        ),
    ]
