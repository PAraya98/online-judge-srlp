from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [('migrations', '0001_initial')]

    operations = [
       migrations.AddField(
            model_name='profile',
            name='display_rank',
            field=models.CharField(max_length=14, default='Alumno', verbose_name=('display rank'), choices=(('Administrador', ('Administrador del sitio')), ('Profesor', ('Acádemico del departamento')), ('Alumno', ('Alumno')), ('Visitante', ('Visitante')))),
            preserve_default=False,
        )
    ]