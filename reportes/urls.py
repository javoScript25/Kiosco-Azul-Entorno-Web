from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.resumen, name="resumen"),
    path("exportar/", views.exportar, name="exportar"),
]
