from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .exportadores import a_excel, a_pdf, nombre_archivo
from .forms import FiltroReporte
from .permisos import solo_administrador
from .servicios import FILTROS_POR_TIPO, REPORTES, armar_reporte


def _filtro(request):
    """Formulario ya validado. Sin parámetros: ventas de hoy."""
    datos = request.GET.copy()
    datos.setdefault("tipo", "ventas")
    datos.setdefault("periodo", "hoy")
    return FiltroReporte(datos)


def _reporte(form):
    d = form.cleaned_data
    return armar_reporte(
        d["tipo"], d["desde"], d["hasta"],
        categoria=d.get("categoria"), medio_pago=d.get("medio_pago"), producto=(d.get("producto") or "").strip(),
    )


@require_GET
@solo_administrador
def resumen(request):
    form = _filtro(request)
    reporte = _reporte(form) if form.is_valid() else None

    tipo = form.data.get("tipo")
    comunes = {k: form.data.get(k) for k in ("periodo", "desde", "hasta") if form.data.get(k)}
    pestanas = [
        {"nombre": nombre, "activa": clave == tipo,
         "url": "?" + urlencode({"tipo": clave, **comunes})}
        for clave, (nombre, _funcion) in REPORTES.items()
    ]
    exportar = (
        {f: reverse("reportes:exportar") + "?" + urlencode({**form.data.dict(), "formato": f}) for f in ("xlsx", "pdf")}
        if reporte and not reporte["vacio"] else None
    )
    return render(request, "reportes/resumen.html", {
        "form": form,
        "reporte": reporte,
        "pestanas": pestanas,
        "exportar": exportar,
        "filtros_visibles": FILTROS_POR_TIPO.get(tipo, ()),
    })


@require_GET
@solo_administrador
def exportar(request):
    form = _filtro(request)
    formato = request.GET.get("formato")
    if not form.is_valid() or formato not in ("xlsx", "pdf"):
        # La pantalla vuelve a mostrar el motivo (período inválido, etc.).
        return redirect(reverse("reportes:resumen") + "?" + urlencode(
            {k: v for k, v in form.data.items() if k != "formato"}))

    reporte = _reporte(form)
    if formato == "xlsx":
        contenido = a_excel(reporte)
        tipo_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        contenido = a_pdf(reporte)
        tipo_mime = "application/pdf"
    respuesta = HttpResponse(contenido, content_type=tipo_mime)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo(reporte, formato)}"'
    return respuesta
