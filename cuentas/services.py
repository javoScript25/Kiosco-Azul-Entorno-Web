"""Reglas de cuentas: aprobación de solicitudes y administración de usuarios (HU-02)."""

from django.contrib.admin.models import LogEntry, CHANGE
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Usuario


@transaction.atomic
def resolver_solicitud(*, usuario_id, aprobar, administrador):
    if not administrador.es_administrador:
        raise PermissionError("Solo el administrador puede resolver solicitudes.")
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    if usuario.estado != Usuario.Estado.PENDIENTE:
        return False
    usuario.estado = Usuario.Estado.APROBADO if aprobar else Usuario.Estado.RECHAZADO
    usuario.is_active = aprobar
    # Una cuenta aprobada desde una solicitud siempre entra como Empleada (OPERADOR).
    usuario.rol = Usuario.Rol.OPERADOR
    usuario.save(update_fields=["estado", "is_active", "rol"])
    LogEntry.objects.log_actions(
        user_id=administrador.pk,
        queryset=Usuario.objects.filter(pk=usuario.pk),
        action_flag=CHANGE,
        change_message="Solicitud aprobada" if aprobar else "Solicitud rechazada",
    )
    return True


def quedaria_sin_administrador(usuario, *, rol, activo):
    """True si el cambio deja al sistema sin ningún ADMINISTRADOR activo."""
    if usuario.pk is None:
        return False
    sigue_siendo_admin = activo and rol == Usuario.Rol.ADMINISTRADOR
    if sigue_siendo_admin:
        return False
    otros = (
        Usuario.objects.select_for_update()
        .filter(rol=Usuario.Rol.ADMINISTRADOR, is_active=True)
        .exclude(pk=usuario.pk)
    )
    era_admin = Usuario.objects.filter(
        pk=usuario.pk, rol=Usuario.Rol.ADMINISTRADOR, is_active=True
    ).exists()
    return era_admin and not otros.exists()


@transaction.atomic
def guardar_usuario(*, form, administrador):
    """Guarda el alta o la edición hecha por el ADMINISTRADOR y deja constancia."""
    if not administrador.es_administrador:
        raise PermissionError("Solo el administrador puede administrar usuarios.")
    usuario = form.instance
    if quedaria_sin_administrador(
        usuario, rol=form.cleaned_data["rol"], activo=form.cleaned_data["is_active"]
    ):
        raise ValidationError(
            "No se puede desactivar ni quitarle el rol al último ADMINISTRADOR activo."
        )
    nuevo = usuario.pk is None
    if form.cleaned_data["is_active"]:
        # Activar una cuenta implica aprobarla (regla activo_solo_aprobado).
        usuario.estado = Usuario.Estado.APROBADO
    usuario = form.save()
    LogEntry.objects.log_actions(
        user_id=administrador.pk,
        queryset=Usuario.objects.filter(pk=usuario.pk),
        action_flag=CHANGE,
        change_message="Usuario creado" if nuevo else "Usuario modificado",
    )
    return usuario
