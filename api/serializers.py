"""Traducción entre las tablas y el JSON del contrato de la API.

Los nombres de los campos son los del diccionario de datos (id_producto, nombre_usuario...).
Las reglas de negocio no se repiten acá: se usan los servicios de cada app.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from caja.models import AperturaCaja
from catalogo.models import Categoria, HistorialPrecio, Producto
from cuentas.models import Usuario
from ventas.models import MedioPago


# ---------------------------------------------------------------- 1.0 Acceso
class SesionSerializer(serializers.Serializer):
    nombre_usuario = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, style={"input_type": "password"})


class UsuarioSerializer(serializers.ModelSerializer):
    id_usuario = serializers.IntegerField(source="pk", read_only=True)
    nombre_usuario = serializers.CharField(source="username", max_length=150)
    nombre = serializers.CharField(source="first_name", max_length=150, allow_blank=True, required=False)
    apellido = serializers.CharField(source="last_name", max_length=150, allow_blank=True, required=False)
    activo = serializers.BooleanField(source="is_active", required=False)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = Usuario
        fields = ("id_usuario", "nombre_usuario", "nombre", "apellido", "email", "rol", "activo", "password")

    def validate_nombre_usuario(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(username__iexact=valor).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya está en uso.")
        return valor

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=valor).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return valor

    def validate(self, datos):
        if self.instance is None and not datos.get("password"):
            raise serializers.ValidationError({"password": "Indicá una contraseña."})
        if datos.get("password"):
            candidato = self.instance or Usuario(
                username=datos.get("username", ""), email=datos.get("email", ""),
                first_name=datos.get("first_name", ""), last_name=datos.get("last_name", ""),
            )
            try:
                validate_password(datos["password"], candidato)
            except Exception as e:
                raise serializers.ValidationError({"password": list(getattr(e, "messages", [str(e)]))})
        return datos


# ---------------------------------------------------------------- 5.0 Catálogo
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("id_categoria", "nombre", "descripcion", "activa")
        read_only_fields = ("id_categoria",)
        extra_kwargs = {"nombre": {"validators": []}}

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("El nombre es obligatorio.")
        if Categoria.objects.filter(nombre__iexact=valor).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ya existe esa categoría.")
        return valor


class ProductoSerializer(serializers.ModelSerializer):
    id_categoria = serializers.PrimaryKeyRelatedField(source="categoria", queryset=Categoria.objects.all())
    categoria = serializers.CharField(source="categoria.nombre", read_only=True)
    en_alerta = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = (
            "id_producto", "codigo_barras", "nombre", "descripcion", "id_categoria", "categoria",
            "unidad_medida", "precio_costo", "precio_venta", "cantidad_actual", "stock_minimo",
            "preventista", "activo", "en_alerta",
        )
        # El stock solo cambia por recepciones, ventas y ajustes (Movimiento_Stock).
        read_only_fields = ("id_producto", "cantidad_actual")
        extra_kwargs = {"codigo_barras": {"validators": []}, "precio_costo": {"required": True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and not request.user.es_administrador:
            # La Empleada no ve costos (preg. 36).
            self.fields.pop("precio_costo")

    def validate_codigo_barras(self, valor):
        valor = valor.strip().upper()
        if not valor:
            raise serializers.ValidationError("El código de barras es obligatorio.")
        if Producto.objects.filter(codigo_barras__iexact=valor).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Ya existe un producto con ese código.")
        return valor

    def validate_id_categoria(self, categoria):
        if not categoria.activa and getattr(self.instance, "categoria_id", None) != categoria.pk:
            raise serializers.ValidationError("La categoría está desactivada.")
        return categoria

    def validate(self, datos):
        costo = datos.get("precio_costo", getattr(self.instance, "precio_costo", None))
        venta = datos.get("precio_venta", getattr(self.instance, "precio_venta", None))
        if costo is not None and venta is not None and venta <= costo:
            raise serializers.ValidationError(
                {"precio_venta": "El precio de venta tiene que ser mayor que el costo."}
            )
        return datos


class HistorialPrecioSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username")

    class Meta:
        model = HistorialPrecio
        fields = ("id_historial_precio", "costo_anterior", "costo_nuevo", "venta_anterior",
                  "venta_nuevo", "usuario", "fecha_hora")


class StockSerializer(serializers.ModelSerializer):
    categoria = serializers.CharField(source="categoria.nombre")
    en_alerta = serializers.BooleanField()

    class Meta:
        model = Producto
        fields = ("id_producto", "codigo_barras", "nombre", "categoria", "unidad_medida",
                  "cantidad_actual", "stock_minimo", "en_alerta")


# ---------------------------------------------------------------- 2.0 y 3.0
class MedioPagoSerializer(serializers.ModelSerializer):
    descripcion = serializers.CharField(source="get_nombre_display", read_only=True)

    class Meta:
        model = MedioPago
        fields = ("id_medio_pago", "nombre", "descripcion", "activo")


class AperturaCajaSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username", read_only=True)
    efectivo_esperado = serializers.SerializerMethodField()

    class Meta:
        model = AperturaCaja
        fields = ("id_apertura_caja", "usuario", "fecha_hora_apertura", "monto_inicial", "estado",
                  "efectivo_esperado")
        read_only_fields = ("id_apertura_caja", "fecha_hora_apertura", "estado")

    def get_efectivo_esperado(self, caja):
        return f"{caja.efectivo_esperado():.2f}"
