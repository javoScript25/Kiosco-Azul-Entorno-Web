"""Carga datos de ejemplo para ver los reportes y sus gráficos.

    python manage.py cargar_datos_demo            -> crea los datos
    python manage.py cargar_datos_demo --borrar   -> los elimina (solo los de ejemplo)

Todo lo que crea queda marcado ("DEMO-" en el código de barras, "[DEMO]" en
concepto/observación), así que --borrar no toca tus datos reales.
"""
import random
from datetime import timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from reportes import modelos as m

MARCA = "[DEMO]"
PREFIJO = "DEMO-"
DIAS = 14

# (categoría, nombre, costo, venta, unidad, stock actual, stock mínimo)
PRODUCTOS = [
    ("Bebidas", "Gaseosa cola 1,5 L", 1400, 2300, "UNIDAD", 6, 12),
    ("Bebidas", "Agua mineral 500 ml", 500, 900, "UNIDAD", 40, 15),
    ("Bebidas", "Jugo en caja", 700, 1200, "UNIDAD", 22, 10),
    ("Golosinas", "Alfajor triple", 600, 1100, "UNIDAD", 50, 20),
    ("Golosinas", "Chocolate 100 g", 1300, 2200, "UNIDAD", 3, 10),
    ("Golosinas", "Caramelos surtidos", 2500, 4200, "KG", 2, 3),
    ("Almacén", "Galletitas dulces", 900, 1600, "UNIDAD", 30, 12),
    ("Almacén", "Yerba 500 g", 2800, 4300, "UNIDAD", 18, 8),
    ("Lácteos", "Leche entera 1 L", 1100, 1700, "UNIDAD", 25, 15),
    ("Lácteos", "Queso cremoso", 7000, 10500, "KG", 4, 3),
]
PESOS_PAGO = ["EFECTIVO"] * 6 + ["TRANSFERENCIA", "DEBITO", "QR"]


def _a(dia, hora, minuto=0):
    """Fecha y hora (con zona horaria) de hace `dia` días."""
    return timezone.localtime().replace(hour=hora, minute=minuto, second=0, microsecond=0) - timedelta(days=dia)


class Command(BaseCommand):
    help = "Carga (o borra con --borrar) datos de ejemplo para probar los reportes."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Elimina los datos de ejemplo.")

    @transaction.atomic
    def handle(self, *args, **opciones):
        if opciones["borrar"]:
            return self._borrar()
        if m.Producto.objects.filter(codigo_barras__startswith=PREFIJO).exists():
            raise CommandError("Ya hay datos de ejemplo. Borralos primero con: python manage.py cargar_datos_demo --borrar")
        usuario = get_user_model().objects.filter(is_active=True).order_by("-is_superuser", "pk").first()
        if usuario is None:
            raise CommandError("No hay ningún usuario. Creá uno con createsuperuser.")
        self._crear(usuario)

    # ------------------------------------------------------------------
    def _crear(self, usuario):
        azar = random.Random(7)
        medios = {n: m.MedioPago.objects.get_or_create(nombre=n)[0] for n in set(PESOS_PAGO)}
        categorias = {}
        productos = []
        campos_producto = {f.name for f in m.Producto._meta.get_fields()}
        for i, (cat, nombre, costo, venta, unidad, stock, minimo) in enumerate(PRODUCTOS, 1):
            if cat not in categorias:
                categorias[cat] = m.Categoria.objects.get_or_create(nombre=f"Demo {cat}")[0]
            datos = dict(
                categoria=categorias[cat], codigo_barras=f"{PREFIJO}{i:03d}", nombre=nombre,
                precio_costo=D(costo), precio_venta=D(venta), unidad_medida=unidad,
                cantidad_actual=D(stock), stock_minimo=D(minimo),
            )
            for campo in ("creado_por", "actualizado_por"):
                if campo in campos_producto:
                    datos[campo] = usuario
            productos.append(m.Producto.objects.create(**datos))

        ventas = 0
        for dia in range(DIAS - 1, -1, -1):
            turno = m.AperturaCaja.objects.create(
                usuario=usuario, fecha_hora_apertura=_a(dia, 8), monto_inicial=D(20000), estado="CERRADA")
            efectivo = D(0)
            for _ in range(azar.randint(2, 5) + (3 if dia in (0, 1, 7) else 0)):
                momento = _a(dia, azar.randint(9, 20), azar.randint(0, 59))
                venta = m.Venta.objects.create(
                    usuario=usuario, apertura_caja=turno, fecha_hora=momento, total=0, estado="CONFIRMADA")
                total = D(0)
                # Los primeros productos se venden más (para que el ranking tenga forma).
                for prod in azar.sample(productos[:6] * 2 + productos[6:], k=azar.randint(1, 3)):
                    cantidad = D(azar.randint(1, 4)) if prod.unidad_medida == "UNIDAD" else D(azar.choice(["0.5", "0.250", "1"]))
                    m.DetalleVenta.objects.create(
                        venta=venta, producto=prod, cantidad=cantidad,
                        precio_unitario=prod.precio_venta, costo_unitario=prod.precio_costo)
                    total += (cantidad * prod.precio_venta).quantize(D("0.01"))
                venta.total = total
                venta.save(update_fields=["total"])
                medio = azar.choice(PESOS_PAGO)
                estado = "PENDIENTE" if (medio == "TRANSFERENCIA" and dia == 0) else "CONFIRMADO"
                m.Pago.objects.create(venta=venta, medio_pago=medios[medio], monto=total, estado=estado, fecha_hora=momento)
                if medio == "EFECTIVO" and estado == "CONFIRMADO":
                    efectivo += total
                ventas += 1
            ingreso = D(azar.choice([1000, 2000]))
            egreso = D(azar.choice([1500, 2500, 3000]))
            m.MovimientoCaja.objects.create(apertura_caja=turno, usuario=usuario, tipo="INGRESO", monto=ingreso, concepto=f"{MARCA} Cambio", fecha_hora=_a(dia, 9))
            m.MovimientoCaja.objects.create(apertura_caja=turno, usuario=usuario, tipo="EGRESO", monto=egreso, concepto=f"{MARCA} Compra de insumos", fecha_hora=_a(dia, 15))
            esperado = D(20000) + efectivo + ingreso - egreso
            contado = max(D(0), esperado + D(azar.choice([-800, -300, 0, 0, 0, 200, 500])))
            m.ArqueoCaja.objects.create(
                apertura_caja=turno, usuario=usuario, tipo="CIERRE",
                efectivo_esperado=esperado, efectivo_contado=contado, fecha_hora=_a(dia, 21))

        ajustes = [
            (0, "AJUSTE_NEGATIVO", "PERDIDA", 2), (1, "AJUSTE_NEGATIVO", "VENCIMIENTO", 3),
            (2, "AJUSTE_NEGATIVO", "ROTURA", 1), (3, "AJUSTE_NEGATIVO", "VENCIMIENTO", 4),
            (4, "AJUSTE_POSITIVO", "CONTEO_FISICO", 2), (5, "AJUSTE_POSITIVO", "ERROR_CARGA", 1),
            (6, "AJUSTE_NEGATIVO", "PERDIDA", 1),
        ]
        for dia, (i, tipo, motivo, cantidad) in enumerate(ajustes):
            m.MovimientoStock.objects.create(
                producto=productos[i], usuario=usuario, tipo=tipo, motivo=motivo, cantidad=D(cantidad),
                observacion=MARCA, fecha_hora=_a(dia, 12))

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(productos)} productos, {DIAS} turnos de caja, {ventas} ventas y {len(ajustes)} ajustes de stock de ejemplo."))
        self.stdout.write("Para borrarlos: python manage.py cargar_datos_demo --borrar")

    # ------------------------------------------------------------------
    def _borrar(self):
        prod = m.Producto.objects.filter(codigo_barras__startswith=PREFIJO)
        ids_ap = list(
            m.MovimientoCaja.objects.filter(concepto__startswith=MARCA)
            .values_list("apertura_caja_id", flat=True).distinct()
        )
        m.MovimientoStock.objects.filter(observacion__startswith=MARCA).delete()
        ventas = m.Venta.objects.filter(apertura_caja_id__in=ids_ap)
        m.Pago.objects.filter(venta__in=ventas).delete()
        m.DetalleVenta.objects.filter(venta__in=ventas).delete()
        n_ventas = ventas.count()
        ventas.delete()
        m.ArqueoCaja.objects.filter(apertura_caja_id__in=ids_ap).delete()
        m.MovimientoCaja.objects.filter(apertura_caja_id__in=ids_ap).delete()
        m.AperturaCaja.objects.filter(pk__in=ids_ap).delete()
        n_prod = prod.count()
        prod.delete()
        m.Categoria.objects.filter(nombre__startswith="Demo ", producto__isnull=True).delete()
        self.stdout.write(self.style.SUCCESS(f"Borrados: {n_prod} productos y {n_ventas} ventas de ejemplo (y su caja y stock)."))