"""Formato, períodos y tipos de celda compartidos por pantalla, Excel y PDF."""
from collections import namedtuple
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

# tipo: texto | pesos | cantidad | entero | porcentaje | fecha | fechahora
Celda = namedtuple("Celda", "valor tipo")
NUMERICOS = {"pesos", "cantidad", "entero", "porcentaje"}

ROTULOS = {
    "EFECTIVO": "Efectivo",
    "TRANSFERENCIA": "Transferencia",
    "DEBITO": "Débito",
    "CREDITO": "Crédito",
    "QR": "QR",
    "RECEPCION": "Recepción",
    "VENTA": "Venta",
    "PERDIDA": "Pérdida",
    "VENCIMIENTO": "Vencimiento",
    "ROTURA": "Rotura",
    "ERROR_CARGA": "Error de carga",
    "CONTEO_FISICO": "Conteo físico",
    "ABIERTA": "Abierta",
    "CERRADA": "Cerrada",
    "INGRESO": "Ingreso",
    "EGRESO": "Egreso",
    "RETIRO": "Retiro",
    "PARCIAL": "Parcial",
    "CIERRE": "Cierre",
}


def rotulo(valor):
    return ROTULOS.get(valor) or str(valor).replace("_", " ").capitalize()


def _separadores(texto):
    # 1,234.50 -> 1.234,50
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def formatear(celda):
    valor, tipo = celda
    if valor is None or valor == "":
        return "—"
    if tipo == "pesos":
        redondo = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return "$ " + _separadores(f"{redondo:,.2f}")
    if tipo == "cantidad":
        texto = f"{Decimal(valor).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP):,.3f}"
        return _separadores(texto.rstrip("0").rstrip("."))
    if tipo == "entero":
        return _separadores(f"{int(valor):,}")
    if tipo == "porcentaje":
        return _separadores(f"{float(valor):,.1f}") + " %"
    if tipo == "fecha":
        return valor.strftime("%d/%m/%Y")
    if tipo == "fechahora":
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M")
    return str(valor)


def nombre_usuario(usuario):
    if usuario is None:
        return ""
    completo = usuario.get_full_name() if hasattr(usuario, "get_full_name") else ""
    return completo or usuario.get_username()


# ---- períodos -------------------------------------------------------------

def resolver_periodo(periodo, desde=None, hasta=None, hoy=None):
    hoy = hoy or timezone.localdate()
    if periodo == "hoy":
        return hoy, hoy
    if periodo == "semana":
        return hoy - timedelta(days=hoy.weekday()), hoy
    if periodo == "mes":
        return hoy.replace(day=1), hoy
    return desde, hasta


def limites(desde, hasta):
    """Instantes [inicio, fin) con zona horaria para filtrar DateTimeField."""
    zona = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona)
    return inicio, fin


def lista_de_dias(desde, hasta):
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


def periodo_anterior(desde, hasta):
    """Mismo largo, inmediatamente antes del período pedido."""
    dias = (hasta - desde).days + 1
    ant_hasta = desde - timedelta(days=1)
    return ant_hasta - timedelta(days=dias - 1), ant_hasta


def variacion(actual, anterior):
    if not anterior:
        return None
    return float((Decimal(actual) - Decimal(anterior)) / Decimal(anterior) * 100)


def tendencia(actual, anterior):
    """(sentido, texto). El texto se entiende sin ver colores ni flechas."""
    pct = variacion(actual, anterior)
    if pct is None:
        return None, "Sin datos del período anterior"
    cifra = formatear(Celda(abs(pct), "porcentaje"))
    if round(pct, 1) == 0:
        return "igual", "Sin cambios respecto del período anterior"
    if pct > 0:
        return "sube", f"Subió {cifra} respecto del período anterior"
    return "baja", f"Bajó {cifra} respecto del período anterior"
