"""Formato único de errores del contrato: {"error": "código", "mensaje": "texto", "campos": {...}}."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _texto(detalle):
    if isinstance(detalle, list):
        return " ".join(_texto(d) for d in detalle)
    if isinstance(detalle, dict):
        return " ".join(_texto(v) for v in detalle.values())
    return str(detalle)


def manejar_error(exc, context):
    if isinstance(exc, DjangoValidationError):
        # Reglas de negocio de los servicios (por ejemplo, "Ya hay una caja abierta").
        exc = exceptions.ValidationError({"no_field_errors": exc.messages})
    if isinstance(exc, Http404):
        return Response({"error": "no_encontrado", "mensaje": "No se encontró el recurso."}, status=404)

    respuesta = exception_handler(exc, context)
    if respuesta is None:
        return None

    if isinstance(exc, exceptions.NotAuthenticated):
        return Response(
            {"error": "sin_sesion", "mensaje": "Iniciá sesión para continuar."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if isinstance(exc, exceptions.ValidationError):
        detalle = exc.detail if isinstance(exc.detail, dict) else {"no_field_errors": exc.detail}
        generales = detalle.pop("no_field_errors", None) or detalle.pop("non_field_errors", None)
        campos = {k: _texto(v) for k, v in detalle.items()}
        mensaje = _texto(generales) if generales else "Revisá los datos marcados."
        return Response({"error": "datos_invalidos", "mensaje": mensaje, "campos": campos}, status=400)

    codigo = {
        401: "sin_sesion",
        403: "acceso_denegado",
        404: "no_encontrado",
        405: "metodo_no_permitido",
    }.get(respuesta.status_code, "error")
    return Response({"error": codigo, "mensaje": _texto(respuesta.data.get("detail", respuesta.data))},
                    status=respuesta.status_code)
