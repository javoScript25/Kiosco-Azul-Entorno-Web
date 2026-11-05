# Kiosco Azul: adapta Categoria y Producto de la plantilla a las tablas del DER
# y agrega Historial_Precio. Conserva los datos existentes (renombra, no borra).

import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_preparar_datos_kiosco_azul"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Restricciones viejas que usan columnas que cambian de nombre.
        migrations.RemoveConstraint(model_name="producto", name="producto_precio_no_negativo"),
        migrations.RemoveConstraint(model_name="producto", name="producto_codigo_sin_mayusculas"),
        # 2. Nombres del diccionario de datos.
        migrations.RenameField(model_name="categoria", old_name="id", new_name="id_categoria"),
        migrations.RenameField(model_name="producto", old_name="id", new_name="id_producto"),
        migrations.RenameField(model_name="producto", old_name="codigo", new_name="codigo_barras"),
        migrations.RenameField(model_name="producto", old_name="precio", new_name="precio_venta"),
        migrations.RenameField(model_name="producto", old_name="stock", new_name="cantidad_actual"),
        migrations.AlterModelTable(name="categoria", table="categoria"),
        migrations.AlterModelTable(name="producto", table="producto"),
        # 3. Tipos y largos del diccionario.
        migrations.AlterField(
            model_name="categoria",
            name="id_categoria",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="producto",
            name="id_producto",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="producto",
            name="codigo_barras",
            field=models.CharField(max_length=50, unique=True, verbose_name="código de barras"),
        ),
        migrations.AlterField(
            model_name="producto",
            name="precio_venta",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="precio de venta",
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="cantidad_actual",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="stock actual",
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="descripcion",
            field=models.CharField(blank=True, max_length=250, verbose_name="descripción"),
        ),
        migrations.AlterField(
            model_name="producto",
            name="categoria",
            field=models.ForeignKey(
                db_column="id_categoria",
                on_delete=django.db.models.deletion.PROTECT,
                to="catalogo.categoria",
                verbose_name="categoría",
            ),
        ),
        # 4. Campos nuevos (los productos existentes quedan con costo 0, por unidad y activos).
        migrations.AddField(
            model_name="categoria",
            name="descripcion",
            field=models.CharField(blank=True, max_length=200, verbose_name="descripción"),
        ),
        migrations.AddField(
            model_name="categoria",
            name="activa",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="producto",
            name="precio_costo",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="precio de costo",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="unidad_medida",
            field=models.CharField(
                choices=[("UNIDAD", "Por unidad"), ("KG", "Por kilo")],
                default="UNIDAD",
                max_length=10,
                verbose_name="unidad de medida",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="stock_minimo",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="stock mínimo",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="preventista",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="producto",
            name="activo",
            field=models.BooleanField(default=True),
        ),
        # 5. Restricciones del diccionario de datos.
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("codigo_barras"),
                name="producto_codigo_sin_mayusculas",
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("precio_costo__gte", 0)), name="producto_costo_no_negativo"
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("precio_venta__gt", 0)), name="producto_precio_venta_positivo"
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("precio_venta__gt", models.F("precio_costo"))),
                name="producto_venta_mayor_costo",
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("cantidad_actual__gte", 0)), name="producto_stock_no_negativo"
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("stock_minimo__gte", 0)),
                name="producto_stock_minimo_no_negativo",
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.CheckConstraint(
                condition=models.Q(("unidad_medida__in", ["UNIDAD", "KG"])),
                name="producto_unidad_lista_cerrada",
            ),
        ),
        # 6. Tabla Historial_Precio.
        migrations.CreateModel(
            name="HistorialPrecio",
            fields=[
                ("id_historial_precio", models.BigAutoField(primary_key=True, serialize=False)),
                ("costo_anterior", models.DecimalField(decimal_places=2, max_digits=12)),
                ("costo_nuevo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("venta_anterior", models.DecimalField(decimal_places=2, max_digits=12)),
                ("venta_nuevo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("fecha_hora", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "producto",
                    models.ForeignKey(
                        db_column="id_producto",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="historial_precios",
                        to="catalogo.producto",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        db_column="id_usuario",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cambios_de_precio",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historial de precio",
                "verbose_name_plural": "historial de precios",
                "db_table": "historial_precio",
                "ordering": ["-fecha_hora", "-pk"],
            },
        ),
    ]
