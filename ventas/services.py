"""Registro de una venta (HU-07): venta, detalle, pagos y movimientos de stock en una
sola transacción (RNF-03). La pantalla de venta llega en el Sprint 5."""

from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from caja.models import AperturaCaja
from catalogo.models import Producto
from inventario.models import MovimientoStock
from .models import DetalleVenta, MedioPago, Pago, Venta

CENTAVO = Decimal("0.01")


@transaction.atomic
def registrar_venta(*, usuario, lineas, pagos):
    """lineas: lista de (producto, cantidad). pagos: lista de (medio_pago, monto, referencia).

    Devuelve (venta, vuelto). Si algo no cumple las reglas no se guarda nada.
    """
    apertura = (
        AperturaCaja.objects.select_for_update()
        .filter(estado=AperturaCaja.Estado.ABIERTA)
        .first()
    )
    if apertura is None:
        raise ValidationError("No hay una caja abierta: abrí la caja antes de vender.")
    if not lineas:
        raise ValidationError("La venta no tiene productos.")

    # Se bloquean los productos en orden para evitar ventas simultáneas sobre el mismo stock.
    ids = sorted({p.pk for p, _ in lineas})
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids).order_by("pk")}
    renglones, total = [], Decimal("0")
    for producto, cantidad in lineas:
        p = productos[producto.pk]
        cantidad = Decimal(str(cantidad))
        if not p.activo:
            raise ValidationError(f"{p.nombre} está dado de baja.")
        if cantidad <= 0:
            raise ValidationError(f"La cantidad de {p.nombre} tiene que ser mayor que 0.")
        if p.unidad_medida == Producto.Unidad.UNIDAD and cantidad != cantidad.to_integral_value():
            raise ValidationError(f"{p.nombre} se vende por unidad: la cantidad tiene que ser entera.")
        if cantidad > p.cantidad_actual:
            raise ValidationError(
                f"No hay stock suficiente de {p.nombre} (quedan {p.cantidad_actual})."
            )
        p.cantidad_actual -= cantidad  # reserva dentro de la transacción
        subtotal = (cantidad * p.precio_venta).quantize(CENTAVO, ROUND_HALF_UP)
        total += subtotal
        renglones.append((p, cantidad))

    no_efectivo = sum(
        (Decimal(str(m)) for mp, m, _ in pagos if mp.nombre != MedioPago.Nombre.EFECTIVO),
        Decimal("0"),
    )
    efectivo_entregado = sum(
        (Decimal(str(m)) for mp, m, _ in pagos if mp.nombre == MedioPago.Nombre.EFECTIVO),
        Decimal("0"),
    )
    if any(Decimal(str(m)) <= 0 for _, m, _ in pagos):
        raise ValidationError("Cada pago tiene que ser mayor que 0.")
    if no_efectivo > total:
        raise ValidationError("Los pagos con tarjeta, QR o transferencia superan el total.")
    if no_efectivo + efectivo_entregado < total:
        raise ValidationError(
            f"Los pagos no cubren el total de $ {total}. Falta $ {total - no_efectivo - efectivo_entregado}."
        )

    venta = Venta.objects.create(
        usuario=usuario, apertura_caja=apertura, total=total, estado=Venta.Estado.CONFIRMADA
    )
    for p, cantidad in renglones:
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=p,
            cantidad=cantidad,
            precio_unitario=p.precio_venta,
            costo_unitario=p.precio_costo,
        )
        p.save(update_fields=["cantidad_actual", "actualizado"])
        MovimientoStock.objects.create(
            producto=p,
            usuario=usuario,
            tipo=MovimientoStock.Tipo.SALIDA_VENTA,
            motivo=MovimientoStock.Motivo.VENTA,
            cantidad=cantidad,
            detalle_venta=detalle,
        )

    efectivo_aplicado = total - no_efectivo
    for medio, monto, referencia in pagos:
        monto = Decimal(str(monto))
        if medio.nombre == MedioPago.Nombre.EFECTIVO:
            continue
        estado = (
            Pago.Estado.PENDIENTE
            if medio.nombre == MedioPago.Nombre.TRANSFERENCIA
            else Pago.Estado.CONFIRMADO
        )
        Pago.objects.create(
            venta=venta, medio_pago=medio, monto=monto, referencia=referencia or "", estado=estado
        )
    if efectivo_aplicado > 0:
        Pago.objects.create(
            venta=venta,
            medio_pago=MedioPago.objects.get(nombre=MedioPago.Nombre.EFECTIVO),
            monto=efectivo_aplicado,
        )
    vuelto = efectivo_entregado - max(efectivo_aplicado, Decimal("0"))
    return venta, vuelto
