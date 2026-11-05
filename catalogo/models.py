"""Proceso 5.0 Gestionar catálogo: tablas Categoria, Producto e Historial_Precio del DER."""

from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone


class Categoria(models.Model):
    id_categoria = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "categoria"
        ordering = ["nombre"]
        verbose_name = "categoría"
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"), name="categoria_nombre_sin_mayusculas"
            )
        ]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class Unidad(models.TextChoices):
        UNIDAD = "UNIDAD", "Por unidad"
        KG = "KG", "Por kilo"

    id_producto = models.BigAutoField(primary_key=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        db_column="id_categoria",
        verbose_name="categoría",
    )
    codigo_barras = models.CharField("código de barras", max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField("descripción", max_length=250, blank=True)
    precio_costo = models.DecimalField(
        "precio de costo",
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    precio_venta = models.DecimalField(
        "precio de venta",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unidad_medida = models.CharField(
        "unidad de medida", max_length=10, choices=Unidad.choices, default=Unidad.UNIDAD
    )
    cantidad_actual = models.DecimalField(
        "stock actual",
        max_digits=10,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    stock_minimo = models.DecimalField(
        "stock mínimo",
        max_digits=10,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )
    preventista = models.CharField(max_length=80, blank=True)
    activo = models.BooleanField(default=True)
    # Auditoría (RNF-04): quién creó y quién modificó por última vez.
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_actualizados",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto"
        ordering = ["nombre", "pk"]
        constraints = [
            models.UniqueConstraint(
                Lower("codigo_barras"), name="producto_codigo_sin_mayusculas"
            ),
            models.CheckConstraint(
                condition=models.Q(precio_costo__gte=0),
                name="producto_costo_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_venta__gt=0),
                name="producto_precio_venta_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_venta__gt=models.F("precio_costo")),
                name="producto_venta_mayor_costo",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_actual__gte=0),
                name="producto_stock_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_minimo__gte=0),
                name="producto_stock_minimo_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(unidad_medida__in=["UNIDAD", "KG"]),
                name="producto_unidad_lista_cerrada",
            ),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:detalle", args=[self.pk])

    @property
    def en_alerta(self):
        return self.activo and self.cantidad_actual <= self.stock_minimo

    @property
    def unidad_corta(self):
        return "kg" if self.unidad_medida == self.Unidad.KG else "u."


class HistorialPrecio(models.Model):
    id_historial_precio = models.BigAutoField(primary_key=True)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="historial_precios",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="cambios_de_precio",
    )
    costo_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    costo_nuevo = models.DecimalField(max_digits=12, decimal_places=2)
    venta_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    venta_nuevo = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "historial_precio"
        ordering = ["-fecha_hora", "-pk"]
        verbose_name = "historial de precio"
        verbose_name_plural = "historial de precios"

    def __str__(self):
        return f"{self.producto} · {self.fecha_hora:%d/%m/%Y %H:%M}"
