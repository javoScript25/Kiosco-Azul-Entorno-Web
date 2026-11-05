"""Datos de prueba ficticios de Kiosco Azul para las 14 tablas.

Uso:  docker compose exec web python manage.py cargar_demo --usuario admin [--con-empleada]

Se puede ejecutar varias veces: no duplica ni modifica registros existentes.
Todos los datos son ficticios (códigos KA-xxx y comprobantes DEMO-xxxx).
"""

import secrets
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from caja.models import AperturaCaja, ArqueoCaja, MovimientoCaja
from caja.services import abrir_caja, arquear, registrar_movimiento
from catalogo.models import Categoria, HistorialPrecio, Producto
from catalogo.services import registrar_cambio_de_precio
from inventario.models import MovimientoStock, RecepcionMercaderia
from inventario.services import ajustar_stock, registrar_recepcion
from ventas.models import MedioPago, Venta
from ventas.services import registrar_venta

CATEGORIAS = [
    ("Bebidas", "Gaseosas, aguas y jugos"),
    ("Lácteos", "Leches, yogures y postres"),
    ("Panificados", "Pan, facturas y galletas de panadería"),
    ("Almacén", "Productos secos y envasados"),
    ("Golosinas", "Alfajores, caramelos y chocolates"),
    ("Limpieza", "Artículos de limpieza"),
    ("Verdulería", "Frutas y verduras, por kilo"),
    ("Fiambrería", "Fiambres y quesos, por kilo"),
]
# código, nombre, categoría, unidad, costo, venta, mínimo, preventista, cantidad recibida
PRODUCTOS = [
    ("KA-001", "Gaseosa cola 500 ml", "Bebidas", "UNIDAD", "900", "1500", "6", "Distribuidora Norte (ficticia)", "24"),
    ("KA-002", "Agua mineral 1,5 L", "Bebidas", "UNIDAD", "700", "1200", "6", "Distribuidora Norte (ficticia)", "18"),
    ("KA-003", "Leche entera 1 L", "Lácteos", "UNIDAD", "1100", "1600", "5", "Lácteos del Valle (ficticio)", "12"),
    ("KA-004", "Yogur bebible 1 L", "Lácteos", "UNIDAD", "1300", "1900", "4", "Lácteos del Valle (ficticio)", "8"),
    ("KA-005", "Pan francés", "Panificados", "KG", "1800", "2800", "3", "Panadería San José (ficticia)", "6.5"),
    ("KA-006", "Galletas de agua 300 g", "Almacén", "UNIDAD", "800", "1300", "5", "", "15"),
    ("KA-007", "Arroz largo fino 1 kg", "Almacén", "UNIDAD", "1200", "1900", "4", "", "10"),
    ("KA-008", "Alfajor triple", "Golosinas", "UNIDAD", "600", "1000", "10", "Golosinas Salta (ficticia)", "30"),
    ("KA-009", "Lavandina 1 L", "Limpieza", "UNIDAD", "700", "1150", "3", "", "6"),
    ("KA-010", "Tomate redondo", "Verdulería", "KG", "1200", "1800", "3", "", "8"),
    ("KA-011", "Banana", "Verdulería", "KG", "1000", "1600", "3", "", "2.5"),
    ("KA-012", "Queso cremoso", "Fiambrería", "KG", "6500", "9500", "1", "", "3.2"),
]


class Command(BaseCommand):
    help = "Carga datos ficticios de Kiosco Azul en las 14 tablas sin modificar registros existentes."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nombre de la Dueña (ADMINISTRADOR) existente")
        parser.add_argument(
            "--con-empleada",
            action="store_true",
            help="Crea el usuario OPERADOR 'empleada' con una contraseña aleatoria que se muestra una vez",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Usuario = get_user_model()
        try:
            duena = Usuario.objects.get(username=options["usuario"].lower(), rol="ADMINISTRADOR", is_active=True)
        except Usuario.DoesNotExist:
            raise CommandError("Primero creá a la Dueña con createsuperuser e indicá su usuario.")

        for nombre in MedioPago.Nombre.values:
            MedioPago.objects.get_or_create(nombre=nombre)

        cats = {}
        for nombre, descripcion in CATEGORIAS:
            cat = Categoria.objects.filter(nombre__iexact=nombre).first()
            cats[nombre] = cat or Categoria.objects.create(nombre=nombre, descripcion=descripcion)

        nuevos = []
        for cod, nombre, cat, unidad, costo, venta, minimo, prev, recibido in PRODUCTOS:
            if Producto.objects.filter(codigo_barras__iexact=cod).exists():
                continue
            p = Producto.objects.create(
                codigo_barras=cod, nombre=nombre, categoria=cats[cat], unidad_medida=unidad,
                precio_costo=costo, precio_venta=venta, stock_minimo=minimo, preventista=prev,
                creado_por=duena, actualizado_por=duena,
            )
            nuevos.append((p, recibido, costo))

        # El stock inicial entra como una recepción de mercadería (tabla Movimiento_Stock tipo ENTRADA).
        if nuevos and not RecepcionMercaderia.objects.filter(nro_comprobante="DEMO-0001").exists():
            registrar_recepcion(
                usuario=duena, lineas=nuevos, nro_comprobante="DEMO-0001",
                observacion="Stock inicial de prueba (datos ficticios)",
            )

        if not HistorialPrecio.objects.exists():
            agua = Producto.objects.filter(codigo_barras="KA-002").first()
            if agua:
                costo, venta = agua.precio_costo, agua.precio_venta
                agua.precio_costo, agua.precio_venta = Decimal("750"), Decimal("1300")
                agua.actualizado_por = duena
                agua.save()
                registrar_cambio_de_precio(producto=agua, costo_anterior=costo, venta_anterior=venta, usuario=duena)

        if not MovimientoStock.objects.filter(tipo="AJUSTE_NEGATIVO").exists():
            yogur = Producto.objects.filter(codigo_barras="KA-004").first()
            if yogur and yogur.cantidad_actual >= 1:
                ajustar_stock(
                    usuario=duena, producto=yogur, tipo="AJUSTE_NEGATIVO", motivo="VENCIMIENTO",
                    cantidad=1, observacion="Yogur vencido (dato de prueba)",
                )

        # Un turno de caja con una venta mixta, un egreso y un arqueo parcial.
        if not AperturaCaja.objects.exists() and not Venta.objects.exists():
            gaseosa = Producto.objects.filter(codigo_barras="KA-001").first()
            tomate = Producto.objects.filter(codigo_barras="KA-010").first()
            if gaseosa and tomate:
                abrir_caja(usuario=duena, monto_inicial=20000)
                efectivo = MedioPago.objects.get(nombre="EFECTIVO")
                transferencia = MedioPago.objects.get(nombre="TRANSFERENCIA")
                registrar_venta(
                    usuario=duena,
                    lineas=[(gaseosa, 2), (tomate, "0.750")],
                    pagos=[(efectivo, 2000, ""), (transferencia, 2350, "TRX-DEMO-0001")],
                )
                registrar_movimiento(
                    usuario=duena, tipo=MovimientoCaja.Tipo.EGRESO, monto=2500,
                    concepto="Compra de bolsas (dato de prueba)",
                )
                caja = AperturaCaja.objects.get(estado="ABIERTA")
                arquear(usuario=duena, tipo=ArqueoCaja.Tipo.PARCIAL, efectivo_contado=caja.efectivo_esperado())

        if options["con_empleada"] and not Usuario.objects.filter(username="empleada").exists():
            clave = secrets.token_urlsafe(9)
            Usuario.objects.create_user(
                "empleada", "empleada@kioscoazul.test", clave, first_name="Empleada",
                last_name="de prueba", rol="OPERADOR", estado="aprobado", is_active=True,
            )
            self.stdout.write(f"Usuario OPERADOR creado: empleada · contraseña: {clave} (anotala, no se vuelve a mostrar)")

        self.stdout.write(self.style.SUCCESS(
            "Datos de prueba de Kiosco Azul disponibles; los registros existentes se conservaron."
        ))
