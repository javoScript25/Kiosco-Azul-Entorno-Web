from rest_framework.permissions import BasePermission, SAFE_METHODS


class EsAdministrador(BasePermission):
    """Solo la Dueña (rol ADMINISTRADOR)."""

    message = "Acceso denegado: esta acción es solo para el ADMINISTRADOR."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.es_administrador)


class LecturaOAdministrador(BasePermission):
    """Cualquiera con sesión puede consultar; solo el ADMINISTRADOR modifica."""

    message = "Acceso denegado: esta acción es solo para el ADMINISTRADOR."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.es_administrador
