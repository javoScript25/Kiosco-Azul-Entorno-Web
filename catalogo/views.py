from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from .forms import CategoriaForm, ProductoForm
from .models import Categoria, Producto
from .services import (
    cambiar_estado_categoria,
    cambiar_estado_producto,
    registrar_cambio_de_precio,
)


class SoloAdministradorMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Solo la Dueña (ADMINISTRADOR) cambia productos, precios y categorías (preg. 36, RNF-02)."""

    def test_func(self):
        return self.request.user.es_administrador


class GuardadoSeguroMixin:
    def despues_de_guardar(self, form):
        """Operaciones extra que deben quedar en la misma transacción."""

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                self.despues_de_guardar(form)
        except IntegrityError:
            form.add_error(
                None,
                "No se pudo guardar: otro registro usa esos datos o cambió una relación. Revisá e intentá de nuevo.",
            )
            return self.form_invalid(form)
        messages.success(self.request, "Cambios guardados.")
        return response


class ProductoListView(LoginRequiredMixin, ListView):
    """Búsqueda de productos (HU-05) y consulta de stock con alertas (HU-14)."""

    model = Producto
    template_name = "catalogo/lista.html"
    paginate_by = 12

    def get_queryset(self):
        qs = super().get_queryset().select_related("categoria")
        if not (self.request.user.es_administrador and self.request.GET.get("inactivos")):
            qs = qs.filter(activo=True)
        q = self.request.GET.get("q", "").strip()[:100]
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_barras__icontains=q))
        categoria = self.request.GET.get("categoria", "")
        if categoria.isdigit():
            qs = qs.filter(categoria_id=int(categoria))
        if self.request.GET.get("alertas"):
            qs = qs.filter(cantidad_actual__lte=F("stock_minimo"))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = Categoria.objects.filter(activa=True)
        ctx["filtros"] = self.request.GET.copy()
        ctx["filtros"].pop("page", None)
        return ctx


class ProductoDetailView(LoginRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/detalle.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.es_administrador:
            ctx["historial"] = self.object.historial_precios.select_related("usuario")[:10]
        return ctx


class ProductoCreateView(SoloAdministradorMixin, GuardadoSeguroMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/formulario.html"

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        form.instance.actualizado_por = self.request.user
        form.instance.cantidad_actual = 0  # el stock entra por una recepción
        return super().form_valid(form)


class ProductoUpdateView(SoloAdministradorMixin, GuardadoSeguroMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/formulario.html"

    def form_valid(self, form):
        form.instance.actualizado_por = self.request.user
        anterior = Producto.objects.only("precio_costo", "precio_venta").get(
            pk=form.instance.pk
        )
        self._costo_anterior = anterior.precio_costo
        self._venta_anterior = anterior.precio_venta
        return super().form_valid(form)

    def despues_de_guardar(self, form):
        registrar_cambio_de_precio(
            producto=self.object,
            costo_anterior=self._costo_anterior,
            venta_anterior=self._venta_anterior,
            usuario=self.request.user,
        )


class ProductoBajaView(SoloAdministradorMixin, View):
    """Baja lógica: el producto deja de venderse pero queda en las ventas pasadas."""

    def get(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        return render(
            request, "catalogo/confirmar_baja.html", {"object": producto, "tipo": "producto"}
        )

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto = cambiar_estado_producto(
            producto_id=pk, activo=not producto.activo, usuario=request.user
        )
        messages.success(
            request,
            "Producto reactivado." if producto.activo else "Producto dado de baja.",
        )
        return redirect(producto.get_absolute_url())


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "catalogo/categorias.html"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.es_administrador else qs.filter(activa=True)


class CategoriaCreateView(SoloAdministradorMixin, GuardadoSeguroMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categorias")


class CategoriaUpdateView(SoloAdministradorMixin, GuardadoSeguroMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categorias")


class CategoriaBajaView(SoloAdministradorMixin, View):
    def get(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)
        return render(
            request, "catalogo/confirmar_baja.html", {"object": categoria, "tipo": "categoria"}
        )

    def post(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)
        try:
            categoria = cambiar_estado_categoria(
                categoria_id=pk, activa=not categoria.activa
            )
        except ValidationError as e:
            return render(
                request,
                "catalogo/confirmar_baja.html",
                {"object": categoria, "tipo": "categoria", "errores": e.messages},
            )
        messages.success(
            request,
            "Categoría reactivada." if categoria.activa else "Categoría desactivada.",
        )
        return redirect("catalogo:categorias")
