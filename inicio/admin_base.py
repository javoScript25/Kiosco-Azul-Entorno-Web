from django.contrib import admin


class SoloLecturaAdmin(admin.ModelAdmin):
    """Consulta de las tablas desde /admin/. Las operaciones se hacen desde las pantallas
    del sistema (o sus servicios), para que siempre se cumplan las reglas del negocio."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
