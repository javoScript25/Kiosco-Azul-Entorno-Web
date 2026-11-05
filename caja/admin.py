from django.contrib import admin
from inicio.admin_base import SoloLecturaAdmin
from .models import AperturaCaja, ArqueoCaja, MovimientoCaja


@admin.register(AperturaCaja)
class AperturaCajaAdmin(SoloLecturaAdmin):
    list_display = ("id_apertura_caja", "fecha_hora_apertura", "usuario", "monto_inicial", "estado")
    list_filter = ("estado",)


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(SoloLecturaAdmin):
    list_display = ("id_movimiento_caja", "apertura_caja", "tipo", "monto", "concepto", "usuario", "fecha_hora")
    list_filter = ("tipo",)


@admin.register(ArqueoCaja)
class ArqueoCajaAdmin(SoloLecturaAdmin):
    list_display = ("id_arqueo", "apertura_caja", "tipo", "efectivo_esperado", "efectivo_contado", "diferencia", "usuario", "fecha_hora")
    list_filter = ("tipo",)
