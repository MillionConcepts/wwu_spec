# Generated by Django 3.1.7 on 2021-02-22 11:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Database',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=100, unique=True)),
                ('url', models.TextField(blank=True, db_index=True)),
                ('description', models.TextField(blank=True, db_index=True)),
                ('short_name', models.CharField(blank=True, db_index=True, max_length=20, null=True)),
                ('citation', models.TextField(blank=True, db_index=True)),
                ('released', models.BooleanField(default=False, verbose_name='Released to Public')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='FilterSet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.CharField(db_index=True, max_length=45, unique=True)),
                ('name', models.CharField(blank=True, db_index=True, max_length=120)),
                ('wavelengths', models.TextField(db_index=True)),
                ('filters', models.TextField(db_index=True)),
                ('illumination', models.TextField(blank=True, db_index=True)),
                ('filter_frequencies', models.TextField(db_index=True)),
                ('url', models.TextField(blank=True, db_index=True)),
                ('description', models.TextField(blank=True, db_index=True)),
                ('display_order', models.IntegerField(blank=True, db_index=True, default=10000)),
            ],
        ),
        migrations.CreateModel(
            name='Library',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=100, unique=True)),
                ('description', models.TextField(blank=True, db_index=True)),
            ],
            options={
                'verbose_name_plural': 'Libraries',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SampleType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20, unique=True, verbose_name='Type Of Sample')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('composition', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Composition')),
                ('date_added', models.DateTimeField(auto_now=True, db_index=True, verbose_name='Date Added')),
                ('filename', models.CharField(blank=True, max_length=80, verbose_name='Name of Uploaded File')),
                ('formula', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Formula')),
                ('grain_size', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Grain Size')),
                ('image', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Path to Image')),
                ('import_notes', models.TextField(blank=True, db_index=True, verbose_name='File import notes')),
                ('locality', models.TextField(blank=True, db_index=True, verbose_name='Locality')),
                ('min_reflectance', models.FloatField(blank=True, db_index=True, verbose_name='Minimum Reflectance')),
                ('sample_name', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Sample Name')),
                ('max_reflectance', models.FloatField(blank=True, db_index=True, verbose_name='Maximum Reflectance')),
                ('other', models.TextField(blank=True, db_index=True, verbose_name='Other Information')),
                ('references', models.TextField(blank=True, db_index=True, verbose_name='References')),
                ('released', models.BooleanField(default=False, verbose_name='Released to Public')),
                ('reflectance', models.TextField(db_index=True, default='[0,0]', verbose_name='Reflectance')),
                ('resolution', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Resolution')),
                ('material_class', models.CharField(blank=True, max_length=40, verbose_name='Material Class')),
                ('sample_desc', models.TextField(blank=True, db_index=True, verbose_name='Sample Description')),
                ('sample_id', models.CharField(db_index=True, max_length=40, verbose_name='Sample ID')),
                ('simulated_spectra', models.TextField(db_index=True, default='{}', verbose_name='Simulated Spectra')),
                ('view_geom', models.CharField(blank=True, db_index=True, max_length=40, verbose_name='Viewing Geometry')),
                ('library', models.ManyToManyField(blank=True, db_index=True, to='vnirsd.Library')),
                ('origin', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vnirsd.database', verbose_name='Database of Origin')),
                ('sample_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='vnirsd.sampletype', verbose_name='Sample Type')),
            ],
            options={
                'ordering': ['sample_id'],
            },
        ),
    ]
