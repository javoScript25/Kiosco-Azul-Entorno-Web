from django import forms
from django.db.models import Q
from .models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    """Alta y modificación de productos (HU-04). El stock no se edita acá:
    entra por una recepción de mercadería y sale por las ventas o los ajustes."""

    class Meta:
        model = Producto
        fields = (
            "codigo_barras",
            "nombre",
            "categoria",
            "descripcion",
            "unidad_medida",
            "precio_costo",
            "precio_venta",
            "stock_minimo",
            "preventista",
        )
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "codigo_barras": "Pasá el lector o escribí un código interno para los productos por peso.",
            "stock_minimo": "Cuando el stock llegue a este valor aparece la alerta de reposición.",
            "preventista": "Preventista o distribuidora que lo provee (opcional).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        filtro = Q(activa=True)
        if self.instance.pk:
            filtro |= Q(pk=self.instance.categoria_id)
        self.fields["categoria"].queryset = Categoria.objects.filter(filtro)
        self.fields["precio_costo"].required = True

    def clean_codigo_barras(self):
        codigo = self.cleaned_data["codigo_barras"].strip().upper()
        if (
            Producto.objects.filter(codigo_barras__iexact=codigo)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe un producto con ese código.")
        return codigo

    def clean(self):
        datos = super().clean()
        costo, venta = datos.get("precio_costo"), datos.get("precio_venta")
        if costo is not None and venta is not None and venta <= costo:
            self.add_error(
                "precio_venta", "El precio de venta tiene que ser mayor que el costo."
            )
        return datos


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ("nombre", "descripcion")

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if (
            Categoria.objects.filter(nombre__iexact=nombre)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Ya existe esa categoría.")
        return nombre
