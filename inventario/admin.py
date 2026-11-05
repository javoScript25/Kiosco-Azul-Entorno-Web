from django.contrib import admin
from inicio.admin_base import SoloLecturaAdmin
from .models import DetalleRecepcion, MovimientoStock, RecepcionMercaderia


class DetalleRecepcionInline(admin.TabularInline):
    model = DetalleRecepcion
    extra = 0
    can_delete = False
    readonly_fields = ("producto", "cantidad", "costo_unitario")


@admin.register(RecepcionMercaderia)
class RecepcionMercaderiaAdmin(SoloLecturaAdmin):
    list_display = ("id_recepcion", "fecha_hora", "nro_comprobante", "usuario", "observacion")
    inlines = [DetalleRecepcionInline]


@admin.register(DetalleRecepcion)
class DetalleRecepcionAdmin(SoloLecturaAdmin):
    list_display = ("id_detalle_recepcion", "recepcion", "producto", "cantidad", "costo_unitario")


@admin.register(MovimientoStock)
class MovimientoStockAdmin(SoloLecturaAdmin):
    list_display = ("id_movimiento_stock", "fecha_hora", "producto", "tipo", "motivo", "cantidad", "usuario", "observacion")
    list_filter = ("tipo", "motivo")
