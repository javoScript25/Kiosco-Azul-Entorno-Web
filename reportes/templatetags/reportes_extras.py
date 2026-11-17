from django import template

from reportes.utiles import NUMERICOS, formatear

register = template.Library()


@register.filter
def formato(celda):
    return formatear(celda)


@register.filter
def clase(celda):
    return "num" if celda.tipo in NUMERICOS else ""
