from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from caja.services import caja_abierta
from catalogo.models import Categoria, Producto
from cuentas.models import Usuario


@login_required
def home(request):
    activos = Producto.objects.filter(activo=True)
    alertas = activos.filter(cantidad_actual__lte=F("stock_minimo")).select_related(
        "categoria"
    )
    return render(
        request,
        "inicio/home.html",
        {
            "productos": activos.count(),
            "categorias": Categoria.objects.filter(activa=True).count(),
            "cantidad_alertas": alertas.count(),
            "alertas": alertas[:8],
            "caja": caja_abierta(),
            "pendientes": (
                Usuario.objects.filter(estado="pendiente").count()
                if request.user.es_administrador
                else None
            ),
        },
    )


def salud(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"estado": "no disponible"}, status=503)
    return JsonResponse({"estado": "ok"})
