from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

app_name = "cuentas"
urlpatterns = [
    path("ingresar/", views.AccesoView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("registrarse/", views.registro, name="registro"),
    path("pendiente/", views.pendiente, name="pendiente"),
    path("solicitudes/", views.solicitudes, name="solicitudes"),
    path("solicitudes/<int:pk>/resolver/", views.resolver, name="resolver"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
]
