from django.urls import path
from . import views as v

app_name = "api"
urlpatterns = [
    # 1.0 Acceso
    path("auth/csrf/", v.CsrfView.as_view(), name="csrf"),
    path("auth/login/", v.LoginView.as_view(), name="login"),
    path("auth/logout/", v.LogoutView.as_view(), name="logout"),
    path("auth/yo/", v.YoView.as_view(), name="yo"),
    path("usuarios/", v.UsuarioLista.as_view(), name="usuarios"),
    path("usuarios/<int:pk>/", v.UsuarioDetalle.as_view(), name="usuario"),
    # 5.0 Catálogo
    path("categorias/", v.CategoriaLista.as_view(), name="categorias"),
    path("categorias/<int:pk>/", v.CategoriaDetalle.as_view(), name="categoria"),
    path("productos/", v.ProductoLista.as_view(), name="productos"),
    path("productos/codigo/<str:codigo>/", v.ProductoPorCodigo.as_view(), name="producto_codigo"),
    path("productos/<int:pk>/", v.ProductoDetalle.as_view(), name="producto"),
    path("productos/<int:pk>/historial-precios/", v.HistorialPrecios.as_view(), name="historial"),
    # 4.0 Inventario (consulta)
    path("stock/", v.StockLista.as_view(), name="stock"),
    # 2.0 y 3.0
    path("medios-pago/", v.MedioPagoLista.as_view(), name="medios_pago"),
    path("cajas/", v.CajaAbrir.as_view(), name="cajas"),
    path("cajas/actual/", v.CajaActual.as_view(), name="caja_actual"),
]
