"""Reglas del catálogo que tocan más de una tabla."""

from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Categoria, HistorialPrecio, Producto


def registrar_cambio_de_precio(*, producto, costo_anterior, venta_anterior, usuario):
    """Guarda una fila en Historial_Precio si cambió el costo o el precio de venta."""
    if (
        producto.precio_costo == costo_anterior
        and producto.precio_venta == venta_anterior
    ):
        return None
    return HistorialPrecio.objects.create(
        producto=producto,
        usuario=usuario,
        costo_anterior=costo_anterior,
        costo_nuevo=producto.precio_costo,
        venta_anterior=venta_anterior,
        venta_nuevo=producto.precio_venta,
    )


@transaction.atomic
def cambiar_estado_producto(*, producto_id, activo, usuario):
    """Baja lógica (o reactivación) de un producto: nunca se borra (HU-04)."""
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    producto.activo = activo
    producto.actualizado_por = usuario
    producto.save(update_fields=["activo", "actualizado_por", "actualizado"])
    return producto


@transaction.atomic
def cambiar_estado_categoria(*, categoria_id, activa):
    """Baja lógica de categoría: no se desactiva si tiene productos activos (HU-03)."""
    categoria = Categoria.objects.select_for_update().get(pk=categoria_id)
    if not activa:
        activos = Producto.objects.filter(categoria=categoria, activo=True).count()
        if activos:
            raise ValidationError(
                f"No se puede desactivar: la categoría tiene {activos} producto"
                f"{'s' if activos != 1 else ''} activo{'s' if activos != 1 else ''}. "
                "Reasignalos o dalos de baja primero."
            )
    categoria.activa = activa
    categoria.save(update_fields=["activa"])
    return categoria
