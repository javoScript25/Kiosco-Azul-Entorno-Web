# Kiosco Azul: agrega el rol del DER (ADMINISTRADOR = Dueña, OPERADOR = Empleada).

from django.db import migrations, models


def asignar_roles(apps, schema_editor):
    Usuario = apps.get_model("cuentas", "Usuario")
    Usuario.objects.filter(is_superuser=True).update(rol="ADMINISTRADOR", is_staff=True)
    Usuario.objects.filter(is_superuser=False).update(rol="OPERADOR", is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="rol",
            field=models.CharField(
                choices=[
                    ("ADMINISTRADOR", "Administrador (Dueña)"),
                    ("OPERADOR", "Operador (Empleada)"),
                ],
                default="OPERADOR",
                max_length=20,
                verbose_name="rol",
            ),
        ),
        migrations.RunPython(asignar_roles, migrations.RunPython.noop),
    ]
