from django.contrib import admin
from inicio.admin_base import SoloLecturaAdmin
from .models import Categoria, HistorialPrecio, Producto

# El catálogo se gestiona desde sus propias pantallas; acá solo se consultan las tablas.


@admin.register(Categoria)
class CategoriaAdmin(SoloLecturaAdmin):
    list_display = ("id_categoria", "nombre", "activa")


@admin.register(Producto)
class ProductoAdmin(SoloLecturaAdmin):
    list_display = ("id_producto", "codigo_barras", "nombre", "categoria", "unidad_medida",
                    "precio_costo", "precio_venta", "cantidad_actual", "stock_minimo", "activo")
    list_filter = ("activo", "unidad_medida", "categoria")
    search_fields = ("nombre", "codigo_barras")


@admin.register(HistorialPrecio)
class HistorialPrecioAdmin(SoloLecturaAdmin):
    list_display = ("producto", "costo_anterior", "costo_nuevo", "venta_anterior",
                    "venta_nuevo", "usuario", "fecha_hora")
