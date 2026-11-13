"""Endpoints de la API REST de Kiosco Azul (prefijo /api/). Ver el contrato en el documento."""

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import F, Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from caja.services import abrir_caja, caja_abierta
from catalogo.models import Categoria, Producto
from catalogo.services import (
    cambiar_estado_categoria,
    cambiar_estado_producto,
    registrar_cambio_de_precio,
)
from cuentas.models import Usuario
from cuentas.services import quedaria_sin_administrador
from ventas.models import MedioPago
from . import serializers as s
from .permisos import EsAdministrador, LecturaOAdministrador


def datos_de_sesion(usuario):
    return {
        "id_usuario": usuario.pk,
        "nombre_usuario": usuario.username,
        "nombre": usuario.get_full_name() or usuario.username,
        "rol": usuario.rol,
    }


# ================================================================ 1.0 Acceso
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Entrega el token CSRF que el frontend envía en el encabezado X-CSRFToken."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        datos = s.SesionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario = authenticate(
            request._request,
            username=datos.validated_data["nombre_usuario"].strip().lower(),
            password=datos.validated_data["password"],
        )
        if getattr(request._request, "axes_locked_out", False):
            return Response(
                {"error": "bloqueado", "mensaje": "Demasiados intentos fallidos. Esperá 15 minutos o pedile a la Dueña que te desbloquee."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if usuario is None:
            return Response(
                {"error": "credenciales_invalidas", "mensaje": "Usuario o contraseña incorrectos."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request._request, usuario)
        return Response(datos_de_sesion(usuario))


class LogoutView(APIView):
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class YoView(APIView):
    def get(self, request):
        return Response(datos_de_sesion(request.user))


class UsuarioLista(generics.ListCreateAPIView):
    permission_classes = [EsAdministrador]
    serializer_class = s.UsuarioSerializer
    queryset = Usuario.objects.exclude(estado=Usuario.Estado.PENDIENTE).order_by("username")

    def perform_create(self, serializer):
        datos = serializer.validated_data
        clave = datos.pop("password")
        activo = datos.pop("is_active", True)
        usuario = Usuario(**datos, is_active=activo,
                          estado=Usuario.Estado.APROBADO if activo else Usuario.Estado.PENDIENTE)
        usuario.set_password(clave)
        usuario.save()
        serializer.instance = usuario


class UsuarioDetalle(generics.RetrieveUpdateAPIView):
    permission_classes = [EsAdministrador]
    serializer_class = s.UsuarioSerializer
    queryset = Usuario.objects.all()
    http_method_names = ["get", "patch", "options"]

    @transaction.atomic
    def perform_update(self, serializer):
        usuario = serializer.instance
        datos = serializer.validated_data
        rol = datos.get("rol", usuario.rol)
        activo = datos.get("is_active", usuario.is_active)
        if quedaria_sin_administrador(usuario, rol=rol, activo=activo):
            raise ValidationError("No se puede desactivar ni quitarle el rol al último ADMINISTRADOR activo.")
        clave = datos.pop("password", None)
        if activo:
            datos["estado"] = Usuario.Estado.APROBADO
        usuario = serializer.save()
        if clave:
            usuario.set_password(clave)
            usuario.save(update_fields=["password"])


# ================================================================ 5.0 Catálogo
class CategoriaLista(generics.ListCreateAPIView):
    permission_classes = [LecturaOAdministrador]
    serializer_class = s.CategoriaSerializer

    def get_queryset(self):
        qs = Categoria.objects.all()
        return qs if self.request.user.es_administrador else qs.filter(activa=True)


class CategoriaDetalle(generics.RetrieveUpdateAPIView):
    permission_classes = [LecturaOAdministrador]
    serializer_class = s.CategoriaSerializer
    queryset = Categoria.objects.all()
    http_method_names = ["get", "patch", "options"]

    @transaction.atomic
    def perform_update(self, serializer):
        activa = serializer.validated_data.pop("activa", None)
        categoria = serializer.save()
        if activa is not None and activa != categoria.activa:
            cambiar_estado_categoria(categoria_id=categoria.pk, activa=activa)


class Paginacion(PageNumberPagination):
    page_size = 20
    page_size_query_param = "por_pagina"
    max_page_size = 100


def productos_visibles(request):
    qs = Producto.objects.select_related("categoria")
    if not (request.user.es_administrador and request.query_params.get("inactivos") == "true"):
        qs = qs.filter(activo=True)
    return qs


class ProductoLista(generics.ListCreateAPIView):
    """GET /api/productos/?buscar=&categoria=&solo_alertas=true&inactivos=true (HU-05, HU-14)."""

    permission_classes = [LecturaOAdministrador]
    serializer_class = s.ProductoSerializer
    pagination_class = Paginacion

    def get_queryset(self):
        qs = productos_visibles(self.request)
        p = self.request.query_params
        buscar = p.get("buscar", "").strip()[:100]
        if buscar:
            qs = qs.filter(
                Q(nombre__icontains=buscar) | Q(codigo_barras__icontains=buscar) | Q(categoria__nombre__icontains=buscar)
            )
        if p.get("categoria", "").isdigit():
            qs = qs.filter(categoria_id=int(p["categoria"]))
        if p.get("solo_alertas") == "true":
            qs = qs.filter(cantidad_actual__lte=F("stock_minimo"))
        return qs.order_by("nombre", "pk")

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user, actualizado_por=self.request.user, cantidad_actual=0)


class ProductoPorCodigo(APIView):
    """GET /api/productos/codigo/{codigo}/: lo que usa el lector de código de barras (HU-05)."""

    def get(self, request, codigo):
        producto = Producto.objects.select_related("categoria").filter(
            codigo_barras__iexact=codigo.strip(), activo=True
        ).first()
        if producto is None:
            return Response({"error": "no_encontrado", "mensaje": "Producto no encontrado."}, status=404)
        return Response(s.ProductoSerializer(producto, context={"request": request}).data)


class ProductoDetalle(generics.RetrieveUpdateAPIView):
    permission_classes = [LecturaOAdministrador]
    serializer_class = s.ProductoSerializer
    http_method_names = ["get", "patch", "options"]

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        return qs if self.request.user.es_administrador else qs.filter(activo=True)

    @transaction.atomic
    def perform_update(self, serializer):
        producto = serializer.instance
        costo, venta = producto.precio_costo, producto.precio_venta
        activo = serializer.validated_data.pop("activo", None)
        producto = serializer.save(actualizado_por=self.request.user)
        registrar_cambio_de_precio(producto=producto, costo_anterior=costo, venta_anterior=venta,
                                   usuario=self.request.user)
        if activo is not None and activo != producto.activo:
            cambiar_estado_producto(producto_id=producto.pk, activo=activo, usuario=self.request.user)
            producto.refresh_from_db()


class HistorialPrecios(generics.ListAPIView):
    permission_classes = [EsAdministrador]
    serializer_class = s.HistorialPrecioSerializer

    def get_queryset(self):
        producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return producto.historial_precios.select_related("usuario")


class StockLista(generics.ListAPIView):
    """GET /api/stock/?solo_alertas=true: stock y alertas para la Dueña y la Empleada (HU-14)."""

    serializer_class = s.StockSerializer

    def get_queryset(self):
        qs = Producto.objects.filter(activo=True).select_related("categoria").order_by("nombre")
        if self.request.query_params.get("solo_alertas") == "true":
            qs = qs.filter(cantidad_actual__lte=F("stock_minimo"))
        return qs


# ================================================================ 2.0 y 3.0
class MedioPagoLista(generics.ListAPIView):
    serializer_class = s.MedioPagoSerializer
    queryset = MedioPago.objects.filter(activo=True)


class CajaAbrir(APIView):
    """POST /api/cajas/ {"monto_inicial": 20000} (HU-06)."""

    def post(self, request):
        datos = s.AperturaCajaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        caja = abrir_caja(usuario=request.user, monto_inicial=datos.validated_data["monto_inicial"])
        return Response(s.AperturaCajaSerializer(caja).data, status=status.HTTP_201_CREATED)


class CajaActual(APIView):
    """GET /api/cajas/actual/: la caja ABIERTA o 404 si no hay ninguna."""

    def get(self, request):
        caja = caja_abierta()
        if caja is None:
            return Response({"error": "sin_caja", "mensaje": "No hay una caja abierta."}, status=404)
        return Response(s.AperturaCajaSerializer(caja).data)
