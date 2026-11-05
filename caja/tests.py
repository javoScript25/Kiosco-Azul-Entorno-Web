from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from catalogo.models import Categoria, Producto
from cuentas.models import Usuario
from inventario.services import registrar_recepcion
from ventas.models import MedioPago
from ventas.services import registrar_venta
from .models import AperturaCaja
from .services import abrir_caja, arquear, registrar_movimiento


class CajaTests(TestCase):
    """HU-06, HU-09 y HU-10: caso correcto y caso de error."""

    def setUp(self):
        self.duena = Usuario.objects.create_superuser("duena", "duena@example.test", "Temporal-segura-298!")
        for n in MedioPago.Nombre.values:
            MedioPago.objects.create(nombre=n)
        cat = Categoria.objects.create(nombre="Bebidas")
        self.gaseosa = Producto.objects.create(
            codigo_barras="KA-001", nombre="Gaseosa", categoria=cat, precio_costo=900, precio_venta=1500,
            creado_por=self.duena, actualizado_por=self.duena,
        )
        registrar_recepcion(usuario=self.duena, lineas=[(self.gaseosa, 10, 900)])

    def test_hu06_una_sola_caja_abierta_y_monto_valido(self):
        abrir_caja(usuario=self.duena, monto_inicial=20000)
        with self.assertRaisesMessage(ValidationError, "Ya hay una caja abierta"):
            abrir_caja(usuario=self.duena, monto_inicial=1000)
        self.assertEqual(AperturaCaja.objects.count(), 1)
        arquear(usuario=self.duena, tipo="CIERRE", efectivo_contado=20000)
        with self.assertRaisesMessage(ValidationError, "negativo"):
            abrir_caja(usuario=self.duena, monto_inicial=-1)

    def test_hu09_movimientos_y_errores(self):
        with self.assertRaisesMessage(ValidationError, "No hay una caja abierta"):
            registrar_movimiento(usuario=self.duena, tipo="INGRESO", monto=100, concepto="x")
        abrir_caja(usuario=self.duena, monto_inicial=5000)
        registrar_movimiento(usuario=self.duena, tipo="INGRESO", monto=1000, concepto="Cambio")
        for monto, concepto, msg in [(0, "x", "mayor que 0"), (100, "  ", "concepto"), (999999, "Pago", "suficiente efectivo")]:
            with self.assertRaisesMessage(ValidationError, msg):
                registrar_movimiento(usuario=self.duena, tipo="EGRESO", monto=monto, concepto=concepto)

    def test_hu10_efectivo_esperado_diferencia_y_cierre(self):
        abrir_caja(usuario=self.duena, monto_inicial=20000)
        efectivo = MedioPago.objects.get(nombre="EFECTIVO")
        transferencia = MedioPago.objects.get(nombre="TRANSFERENCIA")
        # 2 gaseosas = 3000: 1000 por transferencia y 2500 en efectivo -> vuelto 500, efectivo aplicado 2000
        _, vuelto = registrar_venta(usuario=self.duena, lineas=[(self.gaseosa, 2)],
                                    pagos=[(transferencia, 1000, "TRX-1"), (efectivo, 2500, "")])
        self.assertEqual(vuelto, Decimal("500"))
        registrar_movimiento(usuario=self.duena, tipo="EGRESO", monto=3000, concepto="Pago a preventista")
        registrar_movimiento(usuario=self.duena, tipo="RETIRO", monto=1000, concepto="Retiro de la Dueña")
        parcial = arquear(usuario=self.duena, tipo="PARCIAL", efectivo_contado=17500)
        self.assertEqual(parcial.efectivo_esperado, Decimal("18000.00"))
        self.assertEqual(parcial.diferencia, Decimal("-500.00"))
        cierre = arquear(usuario=self.duena, tipo="CIERRE", efectivo_contado=18000)
        self.assertEqual(cierre.diferencia, 0)
        self.assertEqual(AperturaCaja.objects.get().estado, "CERRADA")
        with self.assertRaisesMessage(ValidationError, "No hay una caja abierta"):
            arquear(usuario=self.duena, tipo="CIERRE", efectivo_contado=0)
