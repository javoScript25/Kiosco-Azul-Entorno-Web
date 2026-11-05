from django.contrib.admin.models import LogEntry
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import Usuario


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    },
)
class CuentasTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            "admin", "admin@example.test", "Temporal-segura-298!"
        )
        self.usuario = Usuario.objects.create_user(
            "alumna", "alumna@example.test", "Temporal-segura-298!"
        )

    def test_registro_ignora_privilegios_y_espera_aprobacion(self):
        data = {
            "username": "nuevo",
            "email": "nuevo@example.test",
            "password1": "Otra-segura-782!",
            "password2": "Otra-segura-782!",
            "is_superuser": "true",
            "is_active": "true",
            "estado": "aprobado",
        }
        response = self.client.post(reverse("cuentas:registro"), data)
        self.assertRedirects(response, reverse("cuentas:pendiente"))
        nuevo = Usuario.objects.get(username="nuevo")
        self.assertFalse(nuevo.is_active)
        self.assertFalse(nuevo.is_staff)
        self.assertFalse(nuevo.is_superuser)
        self.assertEqual(nuevo.estado, "pendiente")
        self.assertNotEqual(nuevo.password, data["password1"])
        self.assertTrue(nuevo.check_password(data["password1"]))

    def test_pendiente_no_ingresa(self):
        response = self.client.post(
            reverse("cuentas:login"),
            {"username": "alumna", "password": "Temporal-segura-298!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_aprueba_y_queda_evidencia(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("cuentas:resolver", args=[self.usuario.pk]), {"accion": "aprobar"}
        )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)
        self.assertEqual(self.usuario.estado, "aprobado")
        self.assertEqual(LogEntry.objects.filter(user=self.admin).count(), 1)
        self.client.logout()
        response = self.client.post(
            reverse("cuentas:login"),
            {"username": "ALUMNA", "password": "Temporal-segura-298!"},
        )
        self.assertRedirects(response, reverse("inicio:home"))

    def test_rechazo_e_idempotencia(self):
        self.client.force_login(self.admin)
        url = reverse("cuentas:resolver", args=[self.usuario.pk])
        self.client.post(url, {"accion": "rechazar"})
        self.client.post(url, {"accion": "aprobar"})
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.estado, "rechazado")
        self.assertFalse(self.usuario.is_active)
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_operador_no_puede_aprobar_ni_ver_solicitudes(self):
        self.usuario.estado = "aprobado"
        self.usuario.is_active = True
        self.usuario.save()
        self.client.force_login(self.usuario)
        self.assertEqual(
            self.client.get(reverse("cuentas:solicitudes")).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("cuentas:resolver", args=[self.admin.pk]),
                {"accion": "rechazar"},
            ).status_code,
            403,
        )

    def test_resolver_y_logout_requieren_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(
                reverse("cuentas:resolver", args=[self.usuario.pk])
            ).status_code,
            405,
        )
        self.assertEqual(self.client.get(reverse("cuentas:logout")).status_code, 405)

    def test_accion_desconocida_no_modifica_cuenta(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("cuentas:resolver", args=[self.usuario.pk]),
                {"accion": "inventada"},
            ).status_code,
            403,
        )
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_csrf_en_aprobacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(
            client.post(
                reverse("cuentas:resolver", args=[self.usuario.pk]),
                {"accion": "aprobar"},
            ).status_code,
            403,
        )

    def test_email_duplicado_sin_distinguir_mayusculas(self):
        data = {
            "username": "otra",
            "email": "ALUMNA@example.test",
            "password1": "Otra-segura-782!",
            "password2": "Otra-segura-782!",
        }
        self.assertContains(
            self.client.post(reverse("cuentas:registro"), data),
            "Ese correo ya está registrado",
        )
        self.assertFalse(Usuario.objects.filter(username="otra").exists())

    def test_base_impide_activar_sin_aprobar(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Usuario.objects.filter(pk=self.usuario.pk).update(is_active=True)

    def test_deshabilitar_invalida_acceso_de_sesion(self):
        self.client.force_login(self.admin)
        Usuario.objects.filter(pk=self.admin.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("inicio:home")).status_code, 302)

    def test_no_redireccion_abierta(self):
        response = self.client.post(
            reverse("cuentas:login"),
            {
                "username": "admin",
                "password": "Temporal-segura-298!",
                "next": "https://otro.example/",
            },
        )
        self.assertRedirects(response, reverse("inicio:home"))

    def test_bloqueo_tras_cinco_intentos(self):
        for intento in range(5):
            response = self.client.post(
                reverse("cuentas:login"),
                {"username": "admin", "password": "incorrecta"},
                HTTP_USER_AGENT=f"navegador-{intento}",
                REMOTE_ADDR=f"192.0.2.{intento+1}",
            )
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Demasiados intentos", status_code=429)
        response = self.client.post(
            reverse("cuentas:login"),
            {"username": "admin", "password": "Temporal-segura-298!"},
        )
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_superusuario_creado_normaliza_identidad(self):
        user = Usuario.objects.create_superuser(
            "ADMIN2", "ADMIN2@example.test", "Temporal-segura-298!"
        )
        self.assertTrue(user.is_active)
        self.assertEqual(user.username, "admin2")

    @override_settings(SITE_NAME="Organización de ejemplo")
    def test_nombre_organizacion_en_login(self):
        self.assertContains(
            self.client.get(reverse("cuentas:login")), "Organización de ejemplo"
        )


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
)
class UsuariosYRolesTests(TestCase):
    """HU-01 y HU-02 de Kiosco Azul: roles ADMINISTRADOR (Dueña) y OPERADOR (Empleada)."""

    def setUp(self):
        self.duena = Usuario.objects.create_superuser("duena", "duena@example.test", "Temporal-segura-298!")
        self.empleada = Usuario.objects.create_user(
            "empleada", "empleada@example.test", "Temporal-segura-298!", estado="aprobado", is_active=True
        )

    def test_roles_por_defecto(self):
        self.assertEqual(self.duena.rol, "ADMINISTRADOR")
        self.assertTrue(self.duena.es_administrador)
        self.assertEqual(self.empleada.rol, "OPERADOR")
        self.assertFalse(self.empleada.is_superuser or self.empleada.is_staff)

    def test_hu01_login_muestra_rol_y_operador_no_entra_a_rutas_de_admin(self):
        response = self.client.post(
            reverse("cuentas:login"), {"username": "empleada", "password": "Temporal-segura-298!"}, follow=True
        )
        self.assertContains(response, "Operador (Empleada)")
        self.assertNotContains(response, "Tablas del sistema")
        for url in [reverse("cuentas:usuarios"), reverse("cuentas:usuario_crear"),
                    reverse("cuentas:usuario_editar", args=[self.duena.pk])]:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_hu02_alta_de_usuario_por_la_duena(self):
        self.client.force_login(self.duena)
        data = {"username": "Laura", "first_name": "Laura", "last_name": "Gómez", "email": "laura@example.test",
                "rol": "OPERADOR", "is_active": "on", "password1": "Otra-segura-782!", "password2": "Otra-segura-782!"}
        self.assertRedirects(self.client.post(reverse("cuentas:usuario_crear"), data), reverse("cuentas:usuarios"))
        laura = Usuario.objects.get(username="laura")
        self.assertTrue(laura.is_active)
        self.assertEqual((laura.rol, laura.estado), ("OPERADOR", "aprobado"))
        response = self.client.post(reverse("cuentas:usuario_crear"), {**data, "email": "otra@example.test"})
        self.assertContains(response, "Ese nombre de usuario ya está en uso")

    def test_hu02_cambiar_rol_y_desactivar(self):
        self.client.force_login(self.duena)
        url = reverse("cuentas:usuario_editar", args=[self.empleada.pk])
        datos = {"first_name": "", "last_name": "", "email": "empleada@example.test", "rol": "ADMINISTRADOR", "is_active": "on"}
        self.client.post(url, datos)
        self.empleada.refresh_from_db()
        self.assertTrue(self.empleada.is_superuser and self.empleada.es_administrador)
        self.client.post(url, {**datos, "rol": "OPERADOR", "is_active": ""})
        self.empleada.refresh_from_db()
        self.assertFalse(self.empleada.is_active or self.empleada.is_superuser)

    def test_hu02_no_se_desactiva_al_ultimo_administrador(self):
        self.client.force_login(self.duena)
        url = reverse("cuentas:usuario_editar", args=[self.duena.pk])
        datos = {"email": "duena@example.test", "rol": "OPERADOR", "is_active": "on"}
        self.assertContains(self.client.post(url, datos), "último ADMINISTRADOR activo")
        self.assertContains(self.client.post(url, {**datos, "rol": "ADMINISTRADOR", "is_active": ""}), "último ADMINISTRADOR activo")
        self.duena.refresh_from_db()
        self.assertTrue(self.duena.es_administrador)

    def test_base_rechaza_rol_inconsistente(self):
        for cambio in [{"rol": "CAJERO"}, {"is_superuser": True}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Usuario.objects.filter(pk=self.empleada.pk).update(**cambio)
