from django.urls import path

from . import views

# Rutas internas de la aplicación Análisis
urlpatterns = [
    path("", views.inicio, name="inicio"),

    # Listados de datos (tablas)
    path("listados/regiones/", views.listado_regiones, name="listado_regiones"),
    path("listados/zonas/", views.listado_zonas, name="listado_zonas"),
    path("listados/educacion/", views.listado_educacion, name="listado_educacion"),

    # Gráficos generados con Matplotlib
    path("graficos/barras/", views.grafico_barras, name="grafico_barras"),
    path("graficos/lineas/", views.grafico_lineas, name="grafico_lineas"),
    path("graficos/dispersion/", views.grafico_dispersion, name="grafico_dispersion"),
]
