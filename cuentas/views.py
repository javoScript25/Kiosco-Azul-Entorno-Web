from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import AccesoForm, RegistroForm, UsuarioAltaForm, UsuarioEdicionForm
from .models import Usuario
from .services import guardar_usuario, resolver_solicitud


def solo_administrador(request):
    if not request.user.es_administrador:
        raise PermissionDenied


class AccesoView(LoginView):
    template_name = "cuentas/login.html"
    authentication_form = AccesoForm
    redirect_authenticated_user = True


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio:home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(
                None, "El usuario o correo ya fue registrado. Revisá los datos."
            )
        else:
            return redirect("cuentas:pendiente")
    return render(request, "cuentas/registro.html", {"form": form})


def pendiente(request):
    return render(request, "cuentas/pendiente.html")


@login_required
def solicitudes(request):
    solo_administrador(request)
    return render(
        request,
        "cuentas/solicitudes.html",
        {
            "solicitudes": Usuario.objects.filter(estado="pendiente").order_by(
                "date_joined"
            )
        },
    )


@login_required
@require_POST
def resolver(request, pk):
    solo_administrador(request)
    get_object_or_404(Usuario, pk=pk)
    accion = request.POST.get("accion")
    if accion not in ("aprobar", "rechazar"):
        raise PermissionDenied
    changed = resolver_solicitud(
        usuario_id=pk, aprobar=accion == "aprobar", administrador=request.user
    )
    messages.success(
        request,
        "Solicitud resuelta." if changed else "La solicitud ya había sido resuelta.",
    )
    return redirect("cuentas:solicitudes")


# ---------- HU-02: administración de usuarios y roles (solo ADMINISTRADOR)


@login_required
def usuarios(request):
    solo_administrador(request)
    return render(
        request,
        "cuentas/usuarios.html",
        {"usuarios": Usuario.objects.exclude(estado="pendiente").order_by("username")},
    )


def _guardar(request, form, plantilla, titulo):
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                guardar_usuario(form=form, administrador=request.user)
        except ValidationError as e:
            form.add_error(None, e.messages)
        except IntegrityError:
            form.add_error(None, "No se pudo guardar: el usuario o el correo ya existen.")
        else:
            messages.success(request, "Usuario guardado.")
            return redirect("cuentas:usuarios")
    return render(request, plantilla, {"form": form, "titulo": titulo})


@login_required
def usuario_crear(request):
    solo_administrador(request)
    form = UsuarioAltaForm(request.POST or None)
    return _guardar(request, form, "cuentas/usuario_form.html", "Agregar usuario")


@login_required
def usuario_editar(request, pk):
    solo_administrador(request)
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEdicionForm(request.POST or None, instance=usuario)
    return _guardar(
        request, form, "cuentas/usuario_form.html", f"Editar a {usuario.username}"
    )
