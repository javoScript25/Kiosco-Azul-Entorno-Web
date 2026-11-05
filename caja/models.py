"""Proceso 3.0 Gestionar caja: Apertura_Caja, Movimiento_Caja y Arqueo_Caja del DER."""

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class AperturaCaja(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"

    id_apertura_caja = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="aperturas_caja",
    )
    fecha_hora_apertura = models.DateTimeField(default=timezone.now)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ABIERTA
    )

    class Meta:
        db_table = "apertura_caja"
        ordering = ["-fecha_hora_apertura"]
        verbose_name = "apertura de caja"
        verbose_name_plural = "aperturas de caja"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto_inicial__gte=0),
                name="apertura_monto_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=["ABIERTA", "CERRADA"]),
                name="apertura_estado_lista_cerrada",
            ),
            # Solo puede haber una caja ABIERTA a la vez (HU-06).
            models.UniqueConstraint(
                fields=["estado"],
                condition=models.Q(estado="ABIERTA"),
                name="una_sola_caja_abierta",
            ),
        ]

    def __str__(self):
        return f"Caja {self.pk} · {self.fecha_hora_apertura:%d/%m/%Y %H:%M} · {self.get_estado_display()}"

    def efectivo_esperado(self):
        """inicial + cobros en efectivo + ingresos − egresos − retiros (HU-10)."""
        from ventas.models import Pago, Venta, MedioPago

        cobros = Pago.objects.filter(
            venta__apertura_caja=self,
            venta__estado=Venta.Estado.CONFIRMADA,
            medio_pago__nombre=MedioPago.Nombre.EFECTIVO,
            estado=Pago.Estado.CONFIRMADO,
        ).aggregate(s=Sum("monto"))["s"] or Decimal("0")
        mov = {
            fila["tipo"]: fila["s"]
            for fila in self.movimientos.values("tipo").annotate(s=Sum("monto"))
        }
        return (
            self.monto_inicial
            + cobros
            + mov.get(MovimientoCaja.Tipo.INGRESO, 0)
            - mov.get(MovimientoCaja.Tipo.EGRESO, 0)
            - mov.get(MovimientoCaja.Tipo.RETIRO, 0)
        )


class MovimientoCaja(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"
        RETIRO = "RETIRO", "Retiro"

    id_movimiento_caja = models.BigAutoField(primary_key=True)
    apertura_caja = models.ForeignKey(
        AperturaCaja,
        on_delete=models.PROTECT,
        db_column="id_apertura_caja",
        related_name="movimientos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="movimientos_caja",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    concepto = models.CharField(max_length=200)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "movimiento_caja"
        ordering = ["-fecha_hora"]
        verbose_name = "movimiento de caja"
        verbose_name_plural = "movimientos de caja"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0), name="mov_caja_monto_positivo"
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=["INGRESO", "EGRESO", "RETIRO"]),
                name="mov_caja_tipo_lista_cerrada",
            ),
            models.CheckConstraint(
                condition=~models.Q(concepto=""), name="mov_caja_concepto_obligatorio"
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} $ {self.monto} · {self.concepto}"


class ArqueoCaja(models.Model):
    class Tipo(models.TextChoices):
        PARCIAL = "PARCIAL", "Parcial"
        CIERRE = "CIERRE", "Cierre"

    id_arqueo = models.BigAutoField(primary_key=True)
    apertura_caja = models.ForeignKey(
        AperturaCaja,
        on_delete=models.PROTECT,
        db_column="id_apertura_caja",
        related_name="arqueos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="arqueos_caja",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    efectivo_esperado = models.DecimalField(max_digits=12, decimal_places=2)
    efectivo_contado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "arqueo_caja"
        ordering = ["-fecha_hora"]
        verbose_name = "arqueo de caja"
        verbose_name_plural = "arqueos de caja"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(efectivo_contado__gte=0),
                name="arqueo_contado_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=["PARCIAL", "CIERRE"]),
                name="arqueo_tipo_lista_cerrada",
            ),
            # Un turno se cierra una sola vez.
            models.UniqueConstraint(
                fields=["apertura_caja"],
                condition=models.Q(tipo="CIERRE"),
                name="un_solo_cierre_por_caja",
            ),
        ]

    @property
    def diferencia(self):
        """Dato calculado (no se guarda): contado − esperado."""
        return self.efectivo_contado - self.efectivo_esperado

    def __str__(self):
        return f"{self.get_tipo_display()} de la caja {self.apertura_caja_id}"
