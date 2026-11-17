"""Rutas principales del proyecto."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Todas las rutas del dashboard viven en la aplicación analisis
    path('', include('analisis.urls')),
]
