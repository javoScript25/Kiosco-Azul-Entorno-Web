from decimal import Decimal
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from cuentas.models import Usuario
from .models import Categoria, HistorialPrecio, Producto

AJUSTES = dict(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)


@override_settings(**AJUSTES)
class CatalogoTests(TestCase):
    """HU-03, HU-04, HU-05, HU-14 y HU-16: caso correcto y caso de error."""

    def setUp(self):
        self.admin = Usuario.objects.create_superuser("duena", "duena@example.test", "Temporal-segura-298!")
        self.operador = Usuario.objects.create_user(
            "empleada", "empleada@example.test", "Temporal-segura-298!", estado="aprobado", is_active=True
        )
        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(
            codigo_barras="P-01", nombre="Gaseosa", categoria=self.categoria, precio_costo="900.00",
            precio_venta="1500.00", cantidad_actual=2, stock_minimo=6,
            creado_por=self.admin, actualizado_por=self.admin,
        )
        self.data = {
            "codigo_barras": "p-02", "nombre": "Agua", "categoria": self.categoria.pk,
            "descripcion": "Texto", "unidad_medida": "UNIDAD", "precio_costo": "700",
            "precio_venta": "1200", "stock_minimo": "6", "preventista": "Distribuidora",
        }

    def test_anonimo_no_lee_ni_escribe(self):
        for name, args in [("lista", []), ("detalle", [self.producto.pk]), ("crear", []),
                           ("editar", [self.producto.pk]), ("baja", [self.producto.pk]), ("categorias", [])]:
            self.assertEqual(self.client.get(reverse("catalogo:" + name, args=args)).status_code, 302)
        self.assertEqual(self.client.post(reverse("catalogo:crear"), self.data).status_code, 302)
        self.assertEqual(Producto.objects.count(), 1)

    def test_hu04_alta_con_stock_cero_y_autoria(self):
        self.client.force_login(self.admin)
        self.data["cantidad_actual"] = "50"  # se ignora: el stock entra por recepción
        self.client.post(reverse("catalogo:crear"), self.data)
        p = Producto.objects.get(codigo_barras="P-02")
        self.assertEqual(p.cantidad_actual, 0)
        self.assertEqual(p.creado_por, self.admin)
        self.assertEqual(p.preventista, "Distribuidora")

    def test_hu04_operador_no_modifica_catalogo(self):
        self.client.force_login(self.operador)
        self.assertEqual(self.client.post(reverse("catalogo:crear"), self.data).status_code, 403)
        self.assertEqual(self.client.get(reverse("catalogo:editar", args=[self.producto.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("catalogo:baja", args=[self.producto.pk])).status_code, 403)
        self.assertEqual(Producto.objects.count(), 1)

    def test_hu04_errores_de_validacion(self):
        self.client.force_login(self.admin)
        casos = [("precio_venta", "-1"), ("precio_costo", "-1"), ("categoria", 999999),
                 ("precio_venta", "700"), ("unidad_medida", "LITRO")]
        for campo, valor in casos:
            response = self.client.post(reverse("catalogo:crear"), {**self.data, campo: valor})
            self.assertEqual(response.status_code, 200)
            self.assertIn(campo, response.context["form"].errors)
        self.assertEqual(Producto.objects.count(), 1)

    def test_hu04_codigo_duplicado(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("catalogo:crear"), {**self.data, "codigo_barras": " p-01 "})
        self.assertIn("codigo_barras", response.context["form"].errors)

    def test_restricciones_en_la_base(self):
        for cambio in [{"precio_venta": -1}, {"cantidad_actual": -1}, {"precio_venta": 800},
                       {"unidad_medida": "LITRO"}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Producto.objects.filter(pk=self.producto.pk).update(**cambio)

    def test_hu04_baja_logica_y_reactivacion(self):
        self.client.force_login(self.admin)
        url = reverse("catalogo:baja", args=[self.producto.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)  # visitar la confirmación no cambia nada
        self.client.post(url)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())
        self.client.force_login(self.operador)
        self.assertEqual(self.client.get(reverse("catalogo:lista")).context["paginator"].count, 0)
        self.client.force_login(self.admin)
        self.client.post(url)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)

    def test_hu16_cambio_de_precio_queda_en_historial(self):
        self.client.force_login(self.admin)
        datos = {**self.data, "codigo_barras": "P-01", "nombre": "Gaseosa", "precio_costo": "950", "precio_venta": "1600"}
        self.client.post(reverse("catalogo:editar", args=[self.producto.pk]), datos)
        h = HistorialPrecio.objects.get(producto=self.producto)
        self.assertEqual((h.costo_anterior, h.costo_nuevo), (Decimal("900.00"), Decimal("950.00")))
        self.assertEqual((h.venta_anterior, h.venta_nuevo), (Decimal("1500.00"), Decimal("1600.00")))
        self.assertEqual(h.usuario, self.admin)
        datos["nombre"] = "Gaseosa cola"  # sin cambio de precio: no agrega historial
        self.client.post(reverse("catalogo:editar", args=[self.producto.pk]), datos)
        self.assertEqual(HistorialPrecio.objects.count(), 1)
        self.assertContains(self.client.get(self.producto.get_absolute_url()), "1600,00")

    def test_hu03_categoria_con_productos_activos_no_se_desactiva(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("catalogo:categoria_baja", args=[self.categoria.pk]))
        self.assertContains(response, "1 producto activo")
        self.categoria.refresh_from_db()
        self.assertTrue(self.categoria.activa)

    def test_hu03_crud_categorias_y_permisos(self):
        self.client.force_login(self.operador)
        self.assertEqual(self.client.post(reverse("catalogo:categoria_crear"), {"nombre": "Nueva"}).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("catalogo:categoria_crear"), {"nombre": "Nueva", "descripcion": "x"})
        c = Categoria.objects.get(nombre="Nueva")
        r = self.client.post(reverse("catalogo:categoria_crear"), {"nombre": "nueva"})
        self.assertIn("nombre", r.context["form"].errors)
        self.client.post(reverse("catalogo:categoria_editar", args=[c.pk]), {"nombre": "Actualizada"})
        c.refresh_from_db()
        self.assertEqual(c.nombre, "Actualizada")
        self.client.post(reverse("catalogo:categoria_baja", args=[c.pk]))
        c.refresh_from_db()
        self.assertFalse(c.activa)

    def test_hu05_hu14_busqueda_alertas_y_escape_html(self):
        self.client.force_login(self.operador)
        self.producto.nombre = '<script>alert("x")</script>'
        self.producto.save()
        response = self.client.get(self.producto.get_absolute_url())
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "Precio de costo")  # la Empleada no ve costos
        lista = reverse("catalogo:lista")
        self.assertEqual(self.client.get(lista, {"q": "P-01"}).context["paginator"].count, 1)
        self.assertContains(self.client.get(lista, {"q": "inexistente"}), "No encontramos coincidencias")
        self.assertEqual(self.client.get(lista, {"alertas": "1"}).context["paginator"].count, 1)
        self.assertContains(self.client.get(reverse("inicio:home")), "Quedan 2")
        for n in range(13):
            Producto.objects.create(
                codigo_barras=f"OTRO-{n}", nombre=f"Producto {n}", categoria=self.categoria, precio_venta=10,
                cantidad_actual=50, stock_minimo=1, creado_por=self.admin, actualizado_por=self.admin,
            )
        self.assertEqual(self.client.get(lista, {"alertas": "1"}).context["paginator"].count, 1)
        self.assertEqual(len(self.client.get(lista).context["object_list"]), 12)
        self.assertEqual(len(self.client.get(lista, {"page": 2}).context["object_list"]), 2)

    def test_csrf_impide_modificacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse("catalogo:crear"), self.data).status_code, 403)

    def test_demo_repetible_sin_sobrescribir(self):
        call_command("cargar_demo", usuario="duena", verbosity=0)
        p = Producto.objects.get(codigo_barras="KA-001")
        p.nombre = "Cambiado a mano"
        p.save()
        cantidades = [m.objects.count() for m in (Producto, Categoria, HistorialPrecio)]
        call_command("cargar_demo", usuario="duena", verbosity=0)
        p.refresh_from_db()
        self.assertEqual(p.nombre, "Cambiado a mano")
        self.assertEqual(cantidades, [m.objects.count() for m in (Producto, Categoria, HistorialPrecio)])

    def test_salud_y_pagina_inexistente(self):
        self.assertEqual(self.client.get(reverse("inicio:salud")).json(), {"estado": "ok"})
        self.client.force_login(self.operador)
        self.assertEqual(self.client.get(reverse("catalogo:detalle", args=[999999])).status_code, 404)
