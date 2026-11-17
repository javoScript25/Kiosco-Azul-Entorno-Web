"""Punto único de contacto entre Reportes y el resto del sistema.

Reportes no tiene tablas propias (proceso 6.0): solo lee las de las demás apps.
Los modelos se buscan por NOMBRE DE CLASE, así que no importa en qué app estén.
Los nombres de campo siguen el diccionario de datos de la documentación
(sin el prefijo id_): Venta.fecha_hora, DetalleVenta.costo_unitario, etc.

Si alguna clase se llama distinto en tu código, cambiala en NOMBRES.
"""
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

NOMBRES = {
    "Categoria": "Categoria",
    "Producto": "Producto",
    "MedioPago": "MedioPago",
    "Venta": "Venta",
    "DetalleVenta": "DetalleVenta",
    "Pago": "Pago",
    "AperturaCaja": "AperturaCaja",
    "MovimientoCaja": "MovimientoCaja",
    "ArqueoCaja": "ArqueoCaja",
    "MovimientoStock": "MovimientoStock",
}

# Listas cerradas del diccionario de datos (documentación, "Listas cerradas").
CONFIRMADA = "CONFIRMADA"
CANCELADA = "CANCELADA"
PAGO_CONFIRMADO = "CONFIRMADO"
PAGO_PENDIENTE = "PENDIENTE"
CAJA_ABIERTA = "ABIERTA"
MOV_INGRESO = "INGRESO"
MOV_EGRESO = "EGRESO"
MOV_RETIRO = "RETIRO"
ARQUEO_CIERRE = "CIERRE"
STOCK_ENTRADA = "ENTRADA"
STOCK_AJUSTE_POSITIVO = "AJUSTE_POSITIVO"
STOCK_AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO"
MOTIVOS_REGULARES = ("VENTA", "RECEPCION")
MOTIVOS_PERDIDA = ("PERDIDA", "VENCIMIENTO", "ROTURA")


def _normal(texto):
    # "Medio_Pago" y "MedioDePago" cuentan como el mismo nombre.
    return texto.lower().replace("_", "").replace("de", "")


def _buscar(clase):
    exactos = [m for m in apps.get_models() if m.__name__ == clase]
    encontrados = exactos or [m for m in apps.get_models() if _normal(m.__name__) == _normal(clase)]
    if len(encontrados) != 1:
        raise ImproperlyConfigured(
            f"reportes: esperaba un único modelo llamado {clase!r} y encontré "
            f"{len(encontrados)}. Ajustá NOMBRES en reportes/modelos.py."
        )
    return encontrados[0]


def __getattr__(nombre):
    # Permite escribir modelos.Venta; se resuelve recién al usarlo.
    if nombre in NOMBRES:
        return _buscar(NOMBRES[nombre])
    raise AttributeError(nombre)
