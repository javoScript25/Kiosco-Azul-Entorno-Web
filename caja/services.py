"""Reglas de la caja (HU-06, HU-09 y HU-10). Las pantallas llegan en los sprints 4 a 6."""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from .models import AperturaCaja, ArqueoCaja, MovimientoCaja


def caja_abierta():
    return AperturaCaja.objects.filter(estado=AperturaCaja.Estado.ABIERTA).first()


def abrir_caja(*, usuario, monto_inicial):
    monto_inicial = Decimal(str(monto_inicial))
    if monto_inicial < 0:
        raise ValidationError("El monto inicial no puede ser negativo.")
    try:
        with transaction.atomic():
            return AperturaCaja.objects.create(usuario=usuario, monto_inicial=monto_inicial)
    except IntegrityError:
        raise ValidationError("Ya hay una caja abierta. Cerrala antes de abrir otra.")


@transaction.atomic
def registrar_movimiento(*, usuario, tipo, monto, concepto):
    apertura = (
        AperturaCaja.objects.select_for_update()
        .filter(estado=AperturaCaja.Estado.ABIERTA)
        .first()
    )
    if apertura is None:
        raise ValidationError("No hay una caja abierta.")
    monto = Decimal(str(monto))
    concepto = (concepto or "").strip()
    if monto <= 0:
        raise ValidationError("El monto tiene que ser mayor que 0.")
    if not concepto:
        raise ValidationError("Indicá el concepto del movimiento.")
    if tipo in (MovimientoCaja.Tipo.EGRESO, MovimientoCaja.Tipo.RETIRO):
        if monto > apertura.efectivo_esperado():
            raise ValidationError("No hay suficiente efectivo en la caja para ese monto.")
    return MovimientoCaja.objects.create(
        apertura_caja=apertura, usuario=usuario, tipo=tipo, monto=monto, concepto=concepto
    )


@transaction.atomic
def arquear(*, usuario, tipo, efectivo_contado):
    """Arqueo parcial o cierre. El cierre deja la caja CERRADA."""
    apertura = (
        AperturaCaja.objects.select_for_update()
        .filter(estado=AperturaCaja.Estado.ABIERTA)
        .first()
    )
    if apertura is None:
        raise ValidationError("No hay una caja abierta para arquear.")
    efectivo_contado = Decimal(str(efectivo_contado))
    if efectivo_contado < 0:
        raise ValidationError("El efectivo contado no puede ser negativo.")
    arqueo = ArqueoCaja.objects.create(
        apertura_caja=apertura,
        usuario=usuario,
        tipo=tipo,
        efectivo_esperado=apertura.efectivo_esperado(),
        efectivo_contado=efectivo_contado,
    )
    if tipo == ArqueoCaja.Tipo.CIERRE:
        apertura.estado = AperturaCaja.Estado.CERRADA
        apertura.save(update_fields=["estado"])
    return arqueo
