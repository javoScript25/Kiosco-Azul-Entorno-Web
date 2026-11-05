from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("", include("inicio.urls")),
]
admin.site.site_header = "Kiosco Azul · Tablas del sistema"
admin.site.site_title = "Kiosco Azul"
admin.site.index_title = "Consulta de las 14 tablas del DER"
