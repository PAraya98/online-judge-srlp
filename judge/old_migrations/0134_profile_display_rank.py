# Generated by Django 2.2.28 on 2022-10-05 02:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0133_auto_20221005_0227'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='display_rank',
            field=models.CharField(choices=[('Administrador', 'Administrador del sitio'), ('Profesor', 'Acádemico del departamento'), ('Alumno', 'Alumno'), ('Visitante', 'Visitante')], default='Alumno', max_length=10, verbose_name='display rank'),
        ),
    ]
