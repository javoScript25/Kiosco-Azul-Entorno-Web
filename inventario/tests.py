from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from catalogo.models import Categoria, Producto
from cuentas.models import Usuario
from .models import MovimientoStock, RecepcionMercaderia
from .services import ajustar_stock, registrar_recepcion


class InventarioTests(TestCase):
    """HU-11 y HU-12: caso correcto y caso de error."""

    def setUp(self):
        self.duena = Usuario.objects.create_superuser("duena", "duena@example.test", "Temporal-segura-298!")
        self.empleada = Usuario.objects.create_user(
            "empleada", "e@example.test", "Temporal-segura-298!", estado="aprobado", is_active=True
        )
        cat = Categoria.objects.create(nombre="Lácteos")
        self.yogur = Producto.objects.create(
            codigo_barras="KA-004", nombre="Yogur", categoria=cat, precio_costo=1300, precio_venta=1900,
            creado_por=self.duena, actualizado_por=self.duena,
        )

    def test_hu11_recepcion_suma_stock_y_genera_entrada(self):
        r = registrar_recepcion(usuario=self.duena, lineas=[(self.yogur, 8, 1300)], nro_comprobante="0001-00004521")
        self.yogur.refresh_from_db()
        self.assertEqual(self.yogur.cantidad_actual, 8)
        mov = MovimientoStock.objects.get()
        self.assertEqual((mov.tipo, mov.motivo, mov.detalle_recepcion), ("ENTRADA", "RECEPCION", r.detalles.get()))

    def test_hu11_errores(self):
        with self.assertRaises(PermissionError):
            registrar_recepcion(usuario=self.empleada, lineas=[(self.yogur, 1, 1)])
        with self.assertRaisesMessage(ValidationError, "al menos un producto"):
            registrar_recepcion(usuario=self.duena, lineas=[])
        with self.assertRaisesMessage(ValidationError, "mayor que 0"):
            registrar_recepcion(usuario=self.duena, lineas=[(self.yogur, 0, 1)])
        self.yogur.activo = False
        self.yogur.save()
        with self.assertRaisesMessage(ValidationError, "dado de baja"):
            registrar_recepcion(usuario=self.duena, lineas=[(self.yogur, 1, 1)])
        self.assertEqual(RecepcionMercaderia.objects.count(), 0)

    def test_hu12_ajustes(self):
        registrar_recepcion(usuario=self.duena, lineas=[(self.yogur, 3, 1300)])
        ajustar_stock(usuario=self.duena, producto=self.yogur, tipo="AJUSTE_NEGATIVO", motivo="VENCIMIENTO", cantidad=2)
        self.yogur.refresh_from_db()
        self.assertEqual(self.yogur.cantidad_actual, Decimal("1"))
        with self.assertRaisesMessage(ValidationError, "no puede quedar negativo"):
            ajustar_stock(usuario=self.duena, producto=self.yogur, tipo="AJUSTE_NEGATIVO", motivo="ROTURA", cantidad=5)
        with self.assertRaisesMessage(ValidationError, "motivo"):
            ajustar_stock(usuario=self.duena, producto=self.yogur, tipo="AJUSTE_POSITIVO", motivo="", cantidad=1)
        with self.assertRaises(PermissionError):
            ajustar_stock(usuario=self.empleada, producto=self.yogur, tipo="AJUSTE_POSITIVO", motivo="CONTEO_FISICO", cantidad=1)

    def test_base_exige_origen_de_las_entradas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoStock.objects.create(producto=self.yogur, usuario=self.duena, tipo="ENTRADA",
                                           motivo="RECEPCION", cantidad=1)
