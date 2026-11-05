from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


class AdministradorUsuarios(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        return super()._create_user(
            username.strip().lower(),
            (email or "").strip().lower(),
            password,
            **extra_fields
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Kiosco Azul: quien se crea con createsuperuser es la Dueña (ADMINISTRADOR).
        extra_fields.update(is_active=True, estado="aprobado", rol="ADMINISTRADOR")
        return super().create_superuser(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    """Tabla Usuario del DER.

    Correspondencia con el diccionario de datos:
    id_usuario = id, nombre = first_name + last_name, nombre_usuario = username,
    password_hash = password (lo cifra Django), rol = rol, activo = is_active.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador (Dueña)"
        OPERADOR = "OPERADOR", "Operador (Empleada)"

    email = models.EmailField("correo electrónico", unique=True)
    is_active = models.BooleanField("puede ingresar", default=False)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    rol = models.CharField(
        "rol", max_length=20, choices=Rol.choices, default=Rol.OPERADOR
    )
    objects = AdministradorUsuarios()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="usuario_email_sin_mayusculas"
            ),
            models.UniqueConstraint(
                Lower("username"), name="usuario_nombre_sin_mayusculas"
            ),
            models.CheckConstraint(
                condition=models.Q(is_active=False) | models.Q(estado="aprobado"),
                name="activo_solo_aprobado",
            ),
            models.CheckConstraint(
                condition=models.Q(rol__in=["ADMINISTRADOR", "OPERADOR"]),
                name="usuario_rol_lista_cerrada",
            ),
            # El rol manda: ADMINISTRADOR tiene los permisos de administración de Django
            # y OPERADOR no. La base rechaza cualquier combinación distinta.
            models.CheckConstraint(
                condition=models.Q(rol="ADMINISTRADOR", is_superuser=True, is_staff=True)
                | models.Q(rol="OPERADOR", is_superuser=False, is_staff=False),
                name="usuario_rol_coincide_permisos",
            ),
        ]

    @property
    def es_administrador(self):
        return self.is_active and self.rol == self.Rol.ADMINISTRADOR

    def save(self, *args, **kwargs):
        administrador = self.rol == self.Rol.ADMINISTRADOR
        self.is_superuser = administrador
        self.is_staff = administrador
        campos = kwargs.get("update_fields")
        if campos is not None and "rol" in campos:
            kwargs["update_fields"] = set(campos) | {"is_superuser", "is_staff"}
        super().save(*args, **kwargs)
