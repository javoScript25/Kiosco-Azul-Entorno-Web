from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_usuario_rol"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="usuario",
            constraint=models.CheckConstraint(
                condition=models.Q(("rol__in", ["ADMINISTRADOR", "OPERADOR"])),
                name="usuario_rol_lista_cerrada",
            ),
        ),
        migrations.AddConstraint(
            model_name="usuario",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("is_staff", True), ("is_superuser", True), ("rol", "ADMINISTRADOR")),
                    models.Q(("is_staff", False), ("is_superuser", False), ("rol", "OPERADOR")),
                    _connector="OR",
                ),
                name="usuario_rol_coincide_permisos",
            ),
        ),
    ]
