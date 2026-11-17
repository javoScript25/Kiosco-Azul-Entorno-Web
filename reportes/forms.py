from django import forms

from . import modelos as m
from .servicios import REPORTES
from .utiles import resolver_periodo

PERIODOS = [
    ("hoy", "Hoy"),
    ("semana", "Esta semana"),
    ("mes", "Este mes"),
    ("rango", "Rango de fechas"),
]
MAX_DIAS = 366


class FiltroReporte(forms.Form):
    tipo = forms.ChoiceField(choices=[(k, v[0]) for k, v in REPORTES.items()])
    periodo = forms.ChoiceField(choices=PERIODOS, label="Período")
    desde = forms.DateField(
        required=False, label="Desde",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    hasta = forms.DateField(
        required=False, label="Hasta",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    categoria = forms.ModelChoiceField(queryset=None, required=False, label="Categoría", empty_label="Todas")
    medio_pago = forms.ModelChoiceField(queryset=None, required=False, label="Medio de pago", empty_label="Todos")
    producto = forms.CharField(required=False, max_length=60, label="Producto (nombre o código)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = m.Categoria.objects.filter(activa=True).order_by("nombre")
        self.fields["medio_pago"].queryset = m.MedioPago.objects.filter(activo=True).order_by("nombre")

    def clean(self):
        datos = super().clean()
        periodo = datos.get("periodo")
        if not periodo:
            return datos
        desde, hasta = resolver_periodo(periodo, datos.get("desde"), datos.get("hasta"))
        if not desde or not hasta:
            raise forms.ValidationError("Para un rango de fechas elegí la fecha desde y la fecha hasta.")
        if desde > hasta:
            raise forms.ValidationError("La fecha desde no puede ser mayor que la fecha hasta.")
        if (hasta - desde).days >= MAX_DIAS:
            raise forms.ValidationError(f"El rango no puede superar {MAX_DIAS} días.")
        datos["desde"], datos["hasta"] = desde, hasta
        return datos
