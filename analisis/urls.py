from django.urls import path

from . import views

# Rutas internas de la aplicación Análisis
urlpatterns = [
    path("", views.inicio, name="inicio"),

    # Reportes (listados de datos)
    path("listados/regiones/", views.listado_regiones, name="listado_regiones"),
    path("listados/zonas/", views.listado_zonas, name="listado_zonas"),
    path("listados/educacion/", views.listado_educacion, name="listado_educacion"),
    path("listados/pobreza-zona/", views.listado_pobreza_zona, name="listado_pobreza_zona"),

    # Exportación de reportes (PDF y Excel)
    path("reportes/<str:reporte>/pdf/", views.descargar_pdf, name="descargar_pdf"),
    path("reportes/<str:reporte>/excel/", views.descargar_excel, name="descargar_excel"),

    # Gráficos generados con Matplotlib
    path("graficos/barras/", views.grafico_barras, name="grafico_barras"),
    path("graficos/lineas/", views.grafico_lineas, name="grafico_lineas"),
    path("graficos/dispersion/", views.grafico_dispersion, name="grafico_dispersion"),
    path("grafico-torta/", views.grafico_torta, name="grafico_torta"),
]