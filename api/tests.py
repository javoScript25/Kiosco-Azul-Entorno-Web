from decimal import Decimal
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from caja.models import AperturaCaja
from catalogo.models import Categoria, HistorialPrecio, Producto
from cuentas.models import Usuario
from ventas.models import MedioPago

CLAVE = "Temporal-segura-298!"


@override_settings(SECURE_SSL_REDIRECT=False)
class ApiTests(APITestCase):
    """Sprint 4: API REST. Caso correcto y caso de error de HU-01 a HU-06 y HU-14."""

    def setUp(self):
        self.duena = Usuario.objects.create_superuser("duena", "duena@example.test", CLAVE)
        self.empleada = Usuario.objects.create_user(
            "empleada", "e@example.test", CLAVE, estado="aprobado", is_active=True
        )
        self.cat = Categoria.objects.create(nombre="Bebidas")
        self.gaseosa = Producto.objects.create(
            codigo_barras="KA-001", nombre="Gaseosa cola", categoria=self.cat, precio_costo=900,
            precio_venta=1500, cantidad_actual=2, stock_minimo=6, creado_por=self.duena, actualizado_por=self.duena,
        )
        MedioPago.objects.create(nombre="EFECTIVO")

    # ---------------------------------------------------------------- HU-01
    def test_hu01_login_con_csrf_y_rol(self):
        c = APIClient(enforce_csrf_checks=True)
        token = c.get("/api/auth/csrf/").json()["csrf"]
        r = c.post("/api/auth/login/", {"nombre_usuario": "Empleada", "password": CLAVE}, format="json",
                   HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rol"], "OPERADOR")
        self.assertEqual(c.get("/api/auth/yo/").json()["nombre_usuario"], "empleada")
        # Sin token CSRF, una escritura con sesión se rechaza.
        self.assertEqual(c.post("/api/cajas/", {"monto_inicial": 1}, format="json").status_code, 403)
        c.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value)
        self.assertEqual(c.get("/api/auth/yo/").status_code, 401)

    def test_hu01_login_sin_csrf_rechazado(self):
        c = APIClient(enforce_csrf_checks=True)
        r = c.post("/api/auth/login/", {"nombre_usuario": "empleada", "password": CLAVE}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_hu01_errores_de_login(self):
        r = self.client.post("/api/auth/login/", {"nombre_usuario": "empleada", "password": "mal"}, format="json")
        self.assertEqual((r.status_code, r.json()["error"]), (401, "credenciales_invalidas"))
        self.assertEqual(r.json()["mensaje"], "Usuario o contraseña incorrectos.")
        self.empleada.is_active = False
        self.empleada.save()
        r = self.client.post("/api/auth/login/", {"nombre_usuario": "empleada", "password": CLAVE}, format="json")
        self.assertEqual(r.status_code, 401)
        r = self.client.post("/api/auth/login/", {"nombre_usuario": ""}, format="json")
        self.assertEqual(r.json()["error"], "datos_invalidos")
        self.assertIn("password", r.json()["campos"])

    def test_sin_sesion_responde_401_con_formato_del_contrato(self):
        r = self.client.get("/api/productos/")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(set(r.json()), {"error", "mensaje"})

    # ---------------------------------------------------------------- HU-02
    def test_hu02_usuarios_solo_administrador(self):
        self.client.force_authenticate(self.empleada)
        r = self.client.get("/api/usuarios/")
        self.assertEqual((r.status_code, r.json()["error"]), (403, "acceso_denegado"))
        self.client.force_authenticate(self.duena)
        datos = {"nombre_usuario": "Laura", "nombre": "Laura", "apellido": "Gómez", "email": "laura@example.test",
                 "rol": "OPERADOR", "password": "Otra-segura-782!"}
        r = self.client.post("/api/usuarios/", datos, format="json")
        self.assertEqual(r.status_code, 201)
        laura = Usuario.objects.get(username="laura")
        self.assertTrue(laura.is_active and laura.check_password("Otra-segura-782!"))
        self.assertNotIn("password", r.json())
        r = self.client.post("/api/usuarios/", {**datos, "email": "x@example.test"}, format="json")
        self.assertIn("nombre_usuario", r.json()["campos"])
        r = self.client.post("/api/usuarios/", {**datos, "nombre_usuario": "otra", "email": "o@example.test",
                                                "password": "123"}, format="json")
        self.assertIn("password", r.json()["campos"])

    def test_hu02_no_se_desactiva_al_ultimo_administrador(self):
        self.client.force_authenticate(self.duena)
        r = self.client.patch(f"/api/usuarios/{self.duena.pk}/", {"activo": False}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("último ADMINISTRADOR", r.json()["mensaje"])
        r = self.client.patch(f"/api/usuarios/{self.empleada.pk}/", {"rol": "ADMINISTRADOR"}, format="json")
        self.empleada.refresh_from_db()
        self.assertTrue(self.empleada.es_administrador)

    # ---------------------------------------------------------------- HU-03
    def test_hu03_categorias(self):
        self.client.force_authenticate(self.empleada)
        self.assertEqual(self.client.post("/api/categorias/", {"nombre": "X"}, format="json").status_code, 403)
        self.client.force_authenticate(self.duena)
        r = self.client.post("/api/categorias/", {"nombre": "Lácteos", "descripcion": "Leches"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.client.post("/api/categorias/", {"nombre": "lácteos"}, format="json")
        self.assertIn("nombre", r.json()["campos"])
        r = self.client.patch(f"/api/categorias/{self.cat.pk}/", {"activa": False}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("1 producto activo", r.json()["mensaje"])

    # ---------------------------------------------------------------- HU-04 y HU-16
    def test_hu04_alta_validaciones_y_stock_cero(self):
        self.client.force_authenticate(self.duena)
        datos = {"codigo_barras": "ka-002", "nombre": "Agua", "id_categoria": self.cat.pk, "unidad_medida": "UNIDAD",
                 "precio_costo": "700", "precio_venta": "1200", "stock_minimo": "6", "cantidad_actual": "99"}
        r = self.client.post("/api/productos/", datos, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.json()["codigo_barras"], r.json()["cantidad_actual"]), ("KA-002", "0.000"))
        for cambio, campo in [({"codigo_barras": "KA-001"}, "codigo_barras"), ({"precio_venta": "600"}, "precio_venta"),
                              ({"unidad_medida": "LITRO"}, "unidad_medida"), ({"id_categoria": 9999}, "id_categoria")]:
            r = self.client.post("/api/productos/", {**datos, "codigo_barras": "NUEVO", **cambio}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn(campo, r.json()["campos"])

    def test_hu04_cambio_de_precio_y_baja_logica(self):
        self.client.force_authenticate(self.duena)
        r = self.client.patch(f"/api/productos/{self.gaseosa.pk}/", {"precio_venta": "1600"}, format="json")
        self.assertEqual(r.status_code, 200)
        h = HistorialPrecio.objects.get()
        self.assertEqual((h.venta_anterior, h.venta_nuevo), (Decimal("1500.00"), Decimal("1600.00")))
        r = self.client.patch(f"/api/productos/{self.gaseosa.pk}/", {"precio_venta": "800"}, format="json")
        self.assertIn("precio_venta", r.json()["campos"])
        r = self.client.get(f"/api/productos/{self.gaseosa.pk}/historial-precios/")
        self.assertEqual(len(r.json()), 1)
        self.client.patch(f"/api/productos/{self.gaseosa.pk}/", {"activo": False}, format="json")
        self.gaseosa.refresh_from_db()
        self.assertFalse(self.gaseosa.activo)
        self.client.force_authenticate(self.empleada)
        self.assertEqual(self.client.get(f"/api/productos/{self.gaseosa.pk}/").status_code, 404)

    def test_hu04_empleada_no_modifica_ni_ve_costos(self):
        self.client.force_authenticate(self.empleada)
        r = self.client.patch(f"/api/productos/{self.gaseosa.pk}/", {"precio_venta": "1"}, format="json")
        self.assertEqual(r.status_code, 403)
        datos = self.client.get(f"/api/productos/{self.gaseosa.pk}/").json()
        self.assertNotIn("precio_costo", datos)
        self.assertEqual(self.client.get(f"/api/productos/{self.gaseosa.pk}/historial-precios/").status_code, 403)

    # ---------------------------------------------------------------- HU-05 y HU-14
    def test_hu05_busqueda_y_lector(self):
        self.client.force_authenticate(self.empleada)
        r = self.client.get("/api/productos/", {"buscar": "cola"})
        self.assertEqual(r.json()["count"], 1)
        self.assertEqual(self.client.get("/api/productos/", {"buscar": "bebi"}).json()["count"], 1)
        self.assertEqual(self.client.get("/api/productos/codigo/ka-001/").json()["nombre"], "Gaseosa cola")
        r = self.client.get("/api/productos/codigo/NO-EXISTE/")
        self.assertEqual((r.status_code, r.json()["mensaje"]), (404, "Producto no encontrado."))
        self.gaseosa.activo = False
        self.gaseosa.save()
        self.assertEqual(self.client.get("/api/productos/codigo/KA-001/").status_code, 404)

    def test_hu14_stock_y_alertas(self):
        self.client.force_authenticate(self.empleada)
        r = self.client.get("/api/stock/", {"solo_alertas": "true"})
        self.assertEqual([p["codigo_barras"] for p in r.json()], ["KA-001"])
        self.assertTrue(r.json()[0]["en_alerta"])

    # ---------------------------------------------------------------- HU-06
    def test_hu06_abrir_caja(self):
        self.client.force_authenticate(self.empleada)
        r = self.client.get("/api/cajas/actual/")
        self.assertEqual((r.status_code, r.json()["error"]), (404, "sin_caja"))
        r = self.client.post("/api/cajas/", {"monto_inicial": "20000"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.json()["estado"], r.json()["usuario"]), ("ABIERTA", "empleada"))
        self.assertEqual(self.client.get("/api/cajas/actual/").json()["efectivo_esperado"], "20000.00")
        r = self.client.post("/api/cajas/", {"monto_inicial": "1000"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Ya hay una caja abierta", r.json()["mensaje"])
        self.assertEqual(AperturaCaja.objects.count(), 1)

    def test_hu06_monto_invalido(self):
        self.client.force_authenticate(self.empleada)
        for monto in ("-1", "abc", ""):
            r = self.client.post("/api/cajas/", {"monto_inicial": monto}, format="json")
            self.assertEqual(r.status_code, 400)
        self.assertEqual(AperturaCaja.objects.count(), 0)

    def test_medios_de_pago(self):
        self.client.force_authenticate(self.empleada)
        self.assertEqual(self.client.get("/api/medios-pago/").json()[0]["descripcion"], "Efectivo")

    def test_hu01_bloqueo_tras_cinco_intentos(self):
        for _ in range(5):
            self.client.post("/api/auth/login/", {"nombre_usuario": "empleada", "password": "mal"}, format="json")
        r = self.client.post("/api/auth/login/", {"nombre_usuario": "empleada", "password": CLAVE}, format="json")
        self.assertEqual((r.status_code, r.json()["error"]), (403, "bloqueado"))
