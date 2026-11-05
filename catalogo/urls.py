from django.urls import path
from . import views

app_name = "catalogo"
urlpatterns = [
    path("", views.ProductoListView.as_view(), name="lista"),
    path("nuevo/", views.ProductoCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ProductoDetailView.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="editar"),
    path("<int:pk>/baja/", views.ProductoBajaView.as_view(), name="baja"),
    path("categorias/", views.CategoriaListView.as_view(), name="categorias"),
    path(
        "categorias/nueva/", views.CategoriaCreateView.as_view(), name="categoria_crear"
    ),
    path(
        "categorias/<int:pk>/editar/",
        views.CategoriaUpdateView.as_view(),
        name="categoria_editar",
    ),
    path(
        "categorias/<int:pk>/baja/",
        views.CategoriaBajaView.as_view(),
        name="categoria_baja",
    ),
]
