from django.contrib import admin
from inicio.admin_base import SoloLecturaAdmin
from .models import DetalleVenta, MedioPago, Pago, Venta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    can_delete = False
    readonly_fields = ("producto", "cantidad", "precio_unitario", "costo_unitario")


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    can_delete = False
    readonly_fields = ("medio_pago", "monto", "referencia", "estado", "fecha_hora")


@admin.register(MedioPago)
class MedioPagoAdmin(SoloLecturaAdmin):
    list_display = ("id_medio_pago", "nombre", "activo")


@admin.register(Venta)
class VentaAdmin(SoloLecturaAdmin):
    list_display = ("id_venta", "fecha_hora", "usuario", "apertura_caja", "total", "estado")
    list_filter = ("estado",)
    inlines = [DetalleVentaInline, PagoInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(SoloLecturaAdmin):
    list_display = ("id_detalle_venta", "venta", "producto", "cantidad", "precio_unitario", "costo_unitario")


@admin.register(Pago)
class PagoAdmin(SoloLecturaAdmin):
    list_display = ("id_pago", "venta", "medio_pago", "monto", "referencia", "estado", "fecha_hora")
    list_filter = ("estado", "medio_pago")
