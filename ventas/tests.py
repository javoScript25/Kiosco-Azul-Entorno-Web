from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from caja.services import abrir_caja
from catalogo.models import Categoria, Producto
from cuentas.models import Usuario
from inventario.models import MovimientoStock
from inventario.services import registrar_recepcion
from .models import MedioPago, Pago, Venta
from .services import registrar_venta


class VentaTests(TestCase):
    """HU-07: venta, pagos y stock en una sola transacción (RNF-03)."""

    def setUp(self):
        self.duena = Usuario.objects.create_superuser("duena", "duena@example.test", "Temporal-segura-298!")
        self.empleada = Usuario.objects.create_user(
            "empleada", "e@example.test", "Temporal-segura-298!", estado="aprobado", is_active=True
        )
        for n in MedioPago.Nombre.values:
            MedioPago.objects.create(nombre=n)
        self.efectivo = MedioPago.objects.get(nombre="EFECTIVO")
        self.qr = MedioPago.objects.get(nombre="QR")
        cat = Categoria.objects.create(nombre="Varios")
        crear = lambda c, n, u, v: Producto.objects.create(
            codigo_barras=c, nombre=n, categoria=cat, unidad_medida=u, precio_costo=1, precio_venta=v,
            creado_por=self.duena, actualizado_por=self.duena)
        self.gaseosa = crear("KA-001", "Gaseosa", "UNIDAD", 1500)
        self.tomate = crear("KA-010", "Tomate", "KG", 1800)
        registrar_recepcion(usuario=self.duena, lineas=[(self.gaseosa, 3, 900), (self.tomate, "2.5", 1200)])

    def test_sin_caja_abierta_no_se_vende(self):
        with self.assertRaisesMessage(ValidationError, "No hay una caja abierta"):
            registrar_venta(usuario=self.empleada, lineas=[(self.gaseosa, 1)], pagos=[(self.efectivo, 1500, "")])

    def test_venta_por_unidad_y_por_kilo_descuenta_stock(self):
        abrir_caja(usuario=self.empleada, monto_inicial=0)
        venta, vuelto = registrar_venta(
            usuario=self.empleada, lineas=[(self.gaseosa, 2), (self.tomate, "0.750")],
            pagos=[(self.qr, 1000, "QR-1"), (self.efectivo, 5000, "")],
        )
        self.assertEqual(venta.total, Decimal("4350.00"))
        self.assertEqual(vuelto, Decimal("1650"))
        self.gaseosa.refresh_from_db(); self.tomate.refresh_from_db()
        self.assertEqual(self.gaseosa.cantidad_actual, Decimal("1.000"))
        self.assertEqual(self.tomate.cantidad_actual, Decimal("1.750"))
        self.assertEqual(MovimientoStock.objects.filter(tipo="SALIDA_VENTA").count(), 2)
        self.assertEqual(sorted(p.monto for p in venta.pagos.all()), [Decimal("1000.00"), Decimal("3350.00")])
        d = venta.detalles.get(producto=self.gaseosa)
        self.assertEqual((d.precio_unitario, d.costo_unitario), (Decimal("1500.00"), Decimal("1.00")))

    def test_errores_no_guardan_nada(self):
        abrir_caja(usuario=self.empleada, monto_inicial=0)
        casos = [
            ([(self.gaseosa, 5)], [(self.efectivo, 99999, "")], "No hay stock suficiente"),
            ([(self.gaseosa, "1.5")], [(self.efectivo, 9999, "")], "tiene que ser entera"),
            ([(self.gaseosa, 1)], [(self.efectivo, 1000, "")], "no cubren el total"),
            ([(self.gaseosa, 1)], [(self.qr, 2000, "")], "superan el total"),
            ([], [(self.efectivo, 1, "")], "no tiene productos"),
        ]
        for lineas, pagos, msg in casos:
            with self.assertRaisesMessage(ValidationError, msg):
                registrar_venta(usuario=self.empleada, lineas=lineas, pagos=pagos)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(Pago.objects.count(), 0)
        self.gaseosa.refresh_from_db()
        self.assertEqual(self.gaseosa.cantidad_actual, 3)

    def test_transferencia_queda_pendiente(self):
        abrir_caja(usuario=self.empleada, monto_inicial=0)
        transferencia = MedioPago.objects.get(nombre="TRANSFERENCIA")
        venta, _ = registrar_venta(usuario=self.empleada, lineas=[(self.gaseosa, 1)],
                                   pagos=[(transferencia, 1500, "TRX-9")])
        self.assertEqual(venta.pagos.get().estado, "PENDIENTE")
