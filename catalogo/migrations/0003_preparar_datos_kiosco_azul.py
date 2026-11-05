# Kiosco Azul: deja los datos cargados con la plantilla listos para las reglas nuevas.
# - La descripción pasa a VARCHAR(250): se recortan las más largas.
# - El precio de venta pasa a ser > 0 y > costo: un precio 0 queda en 0,01 para revisarlo.

from decimal import Decimal
from django.db import migrations


def preparar(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for p in Producto.objects.all():
        cambios = {}
        if len(p.descripcion) > 250:
            cambios["descripcion"] = p.descripcion[:250]
        if p.precio <= 0:
            cambios["precio"] = Decimal("0.01")
        if cambios:
            Producto.objects.filter(pk=p.pk).update(**cambios)


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_initial"),
    ]

    operations = [migrations.RunPython(preparar, migrations.RunPython.noop)]
