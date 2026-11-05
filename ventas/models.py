"""Proceso 2.0 Registrar ventas: Medio_Pago, Venta, Detalle_Venta y Pago del DER."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class MedioPago(models.Model):
    class Nombre(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        DEBITO = "DEBITO", "Tarjeta de débito"
        CREDITO = "CREDITO", "Tarjeta de crédito"
        QR = "QR", "QR"

    id_medio_pago = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=30, choices=Nombre.choices, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "medio_pago"
        ordering = ["pk"]
        verbose_name = "medio de pago"
        verbose_name_plural = "medios de pago"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    nombre__in=["EFECTIVO", "TRANSFERENCIA", "DEBITO", "CREDITO", "QR"]
                ),
                name="medio_pago_lista_cerrada",
            )
        ]

    def __str__(self):
        return self.get_nombre_display()


class Venta(models.Model):
    class Estado(models.TextChoices):
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"

    id_venta = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="ventas",
    )
    apertura_caja = models.ForeignKey(
        "caja.AperturaCaja",
        on_delete=models.PROTECT,
        db_column="id_apertura_caja",
        related_name="ventas",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.CONFIRMADA
    )

    class Meta:
        db_table = "venta"
        ordering = ["-fecha_hora", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0), name="venta_total_no_negativo"
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["SUSPENDIDA", "CONFIRMADA", "CANCELADA"]),
                name="venta_estado_lista_cerrada",
            ),
        ]

    def __str__(self):
        return f"Venta {self.pk} · $ {self.total}"


class DetalleVenta(models.Model):
    id_detalle_venta = models.BigAutoField(primary_key=True)
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, db_column="id_venta", related_name="detalles"
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="detalles_venta",
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_venta"
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="det_venta_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gt=0),
                name="det_venta_precio_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(costo_unitario__gte=0),
                name="det_venta_costo_no_negativo",
            ),
        ]

    @property
    def subtotal(self):
        """Dato calculado (no se guarda): cantidad × precio_unitario."""
        return (self.cantidad * self.precio_unitario).quantize(self.precio_unitario)

    def __str__(self):
        return f"{self.cantidad} × {self.producto}"


class Pago(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    id_pago = models.BigAutoField(primary_key=True)
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, db_column="id_venta", related_name="pagos"
    )
    medio_pago = models.ForeignKey(
        MedioPago,
        on_delete=models.PROTECT,
        db_column="id_medio_pago",
        related_name="pagos",
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    referencia = models.CharField(max_length=100, blank=True)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.CONFIRMADO
    )
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "pago"
        ordering = ["-fecha_hora", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0), name="pago_monto_positivo"
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["PENDIENTE", "CONFIRMADO", "RECHAZADO"]),
                name="pago_estado_lista_cerrada",
            ),
        ]

    def __str__(self):
        return f"{self.medio_pago} $ {self.monto} ({self.get_estado_display()})"
