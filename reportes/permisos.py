from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_administrador(usuario):
    valor = getattr(usuario, "es_administrador", False)
    # Si en tu modelo es un método y no una propiedad, siempre sería "verdadero".
    return bool(valor() if callable(valor) else valor)


def solo_administrador(vista):
    """RNF-02: los reportes los ve únicamente el ADMINISTRADOR (la Dueña)."""

    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura
