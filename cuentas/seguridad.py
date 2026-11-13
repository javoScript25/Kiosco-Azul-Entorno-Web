def sin_ip(request):
    """Limitamos por cuenta, sin bloquear a toda el aula que comparte una IP."""
    return None


def respuesta_de_bloqueo(request, original_response=None, credentials=None):
    """La API recibe el bloqueo en JSON (formato del contrato); las páginas, la plantilla HTML."""
    from django.http import JsonResponse
    from django.shortcuts import render

    if request.path.startswith("/api/"):
        return JsonResponse(
            {"error": "bloqueado",
             "mensaje": "Demasiados intentos fallidos. Esperá 15 minutos o pedile a la Dueña que te desbloquee."},
            status=403,
        )
    return render(request, "cuentas/bloqueo.html", status=429)
