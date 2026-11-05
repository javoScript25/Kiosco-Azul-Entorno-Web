"""Proceso 4.0 Gestionar inventario: Recepcion_Mercaderia, Detalle_Recepcion y Movimiento_Stock."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class RecepcionMercaderia(models.Model):
    id_recepcion = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="recepciones",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    nro_comprobante = models.CharField(
        "nro. de factura o remito", max_length=30, blank=True
    )
    observacion = models.CharField("observación", max_length=250, blank=True)

    class Meta:
        db_table = "recepcion_mercaderia"
        ordering = ["-fecha_hora", "-pk"]
        verbose_name = "recepción de mercadería"
        verbose_name_plural = "recepciones de mercadería"

    def __str__(self):
        return f"Recepción {self.pk} · {self.nro_comprobante or 'sin comprobante'}"


class DetalleRecepcion(models.Model):
    id_detalle_recepcion = models.BigAutoField(primary_key=True)
    recepcion = models.ForeignKey(
        RecepcionMercaderia,
        on_delete=models.CASCADE,
        db_column="id_recepcion",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="detalles_recepcion",
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_recepcion"
        verbose_name = "detalle de recepción"
        verbose_name_plural = "detalles de recepción"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="det_recep_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(costo_unitario__gte=0),
                name="det_recep_costo_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"


class MovimientoStock(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA_VENTA = "SALIDA_VENTA", "Salida por venta"
        AJUSTE_POSITIVO = "AJUSTE_POSITIVO", "Ajuste positivo"
        AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO", "Ajuste negativo"

    class Motivo(models.TextChoices):
        RECEPCION = "RECEPCION", "Recepción"
        VENTA = "VENTA", "Venta"
        PERDIDA = "PERDIDA", "Pérdida"
        VENCIMIENTO = "VENCIMIENTO", "Vencimiento"
        ROTURA = "ROTURA", "Rotura"
        ERROR_CARGA = "ERROR_CARGA", "Error de carga"
        CONTEO_FISICO = "CONTEO_FISICO", "Conteo físico"

    id_movimiento_stock = models.BigAutoField(primary_key=True)
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="movimientos_stock",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="movimientos_stock",
    )
    tipo = models.CharField(max_length=16, choices=Tipo.choices)
    motivo = models.CharField(max_length=16, choices=Motivo.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    # Relaciones 1:1 opcionales del DER (decisión: un movimiento nace de una sola línea).
    detalle_venta = models.OneToOneField(
        "ventas.DetalleVenta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_detalle_venta",
        related_name="movimiento_stock",
    )
    detalle_recepcion = models.OneToOneField(
        DetalleRecepcion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="id_detalle_recepcion",
        related_name="movimiento_stock",
    )
    observacion = models.CharField("observación", max_length=200, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "movimiento_stock"
        ordering = ["-fecha_hora", "-pk"]
        verbose_name = "movimiento de stock"
        verbose_name_plural = "movimientos de stock"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="mov_stock_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    tipo__in=["ENTRADA", "SALIDA_VENTA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"]
                ),
                name="mov_stock_tipo_lista_cerrada",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    motivo__in=[
                        "RECEPCION",
                        "VENTA",
                        "PERDIDA",
                        "VENCIMIENTO",
                        "ROTURA",
                        "ERROR_CARGA",
                        "CONTEO_FISICO",
                    ]
                ),
                name="mov_stock_motivo_lista_cerrada",
            ),
            # Una entrada nace de una recepción; una salida por venta, de una línea de venta.
            models.CheckConstraint(
                condition=~models.Q(tipo="ENTRADA")
                | models.Q(detalle_recepcion__isnull=False),
                name="mov_stock_entrada_con_recepcion",
            ),
            models.CheckConstraint(
                condition=~models.Q(tipo="SALIDA_VENTA")
                | models.Q(detalle_venta__isnull=False),
                name="mov_stock_salida_con_venta",
            ),
            models.CheckConstraint(
                condition=models.Q(detalle_venta__isnull=True)
                | models.Q(detalle_recepcion__isnull=True),
                name="mov_stock_un_solo_origen",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad} · {self.producto}"
