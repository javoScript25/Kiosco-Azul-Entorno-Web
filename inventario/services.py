"""Reglas de inventario (HU-11 y HU-12): todo cambio de stock deja un Movimiento_Stock."""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from catalogo.models import Producto
from .models import DetalleRecepcion, MovimientoStock, RecepcionMercaderia


def _solo_administrador(usuario):
    if not usuario.es_administrador:
        raise PermissionError("Solo la Dueña (ADMINISTRADOR) puede modificar el stock.")


@transaction.atomic
def registrar_recepcion(*, usuario, lineas, nro_comprobante="", observacion=""):
    """lineas: lista de (producto, cantidad, costo_unitario)."""
    _solo_administrador(usuario)
    if not lineas:
        raise ValidationError("La recepción tiene que tener al menos un producto.")
    recepcion = RecepcionMercaderia.objects.create(
        usuario=usuario, nro_comprobante=nro_comprobante, observacion=observacion
    )
    for producto, cantidad, costo in lineas:
        cantidad, costo = Decimal(str(cantidad)), Decimal(str(costo))
        p = Producto.objects.select_for_update().get(pk=producto.pk)
        if not p.activo:
            raise ValidationError(f"{p.nombre} está dado de baja.")
        if cantidad <= 0:
            raise ValidationError(f"La cantidad de {p.nombre} tiene que ser mayor que 0.")
        detalle = DetalleRecepcion.objects.create(
            recepcion=recepcion, producto=p, cantidad=cantidad, costo_unitario=costo
        )
        p.cantidad_actual += cantidad
        p.save(update_fields=["cantidad_actual", "actualizado"])
        MovimientoStock.objects.create(
            producto=p,
            usuario=usuario,
            tipo=MovimientoStock.Tipo.ENTRADA,
            motivo=MovimientoStock.Motivo.RECEPCION,
            cantidad=cantidad,
            detalle_recepcion=detalle,
        )
    return recepcion


@transaction.atomic
def ajustar_stock(*, usuario, producto, tipo, motivo, cantidad, observacion=""):
    _solo_administrador(usuario)
    if tipo not in (MovimientoStock.Tipo.AJUSTE_POSITIVO, MovimientoStock.Tipo.AJUSTE_NEGATIVO):
        raise ValidationError("Un ajuste es positivo o negativo.")
    if motivo in (MovimientoStock.Motivo.RECEPCION, MovimientoStock.Motivo.VENTA, "", None):
        raise ValidationError("Elegí el motivo del ajuste.")
    cantidad = Decimal(str(cantidad))
    if cantidad <= 0:
        raise ValidationError("La cantidad tiene que ser mayor que 0.")
    p = Producto.objects.select_for_update().get(pk=producto.pk)
    if tipo == MovimientoStock.Tipo.AJUSTE_NEGATIVO:
        if cantidad > p.cantidad_actual:
            raise ValidationError(
                f"El stock de {p.nombre} no puede quedar negativo (hay {p.cantidad_actual})."
            )
        p.cantidad_actual -= cantidad
    else:
        p.cantidad_actual += cantidad
    p.save(update_fields=["cantidad_actual", "actualizado"])
    return MovimientoStock.objects.create(
        producto=p,
        usuario=usuario,
        tipo=tipo,
        motivo=motivo,
        cantidad=cantidad,
        observacion=observacion,
    )
