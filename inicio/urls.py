from django.urls import path
from . import views

app_name = "inicio"
urlpatterns = [
    path("", views.home, name="home"),
    path("salud/", views.salud, name="salud"),
]
