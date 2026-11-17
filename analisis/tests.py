from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

REPORTES = ["regiones", "zonas", "educacion", "pobreza_zona"]


class ReportesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "casen", "sunburst", verbosity=0)

    def test_paginas_principales(self):
        for nombre in ["inicio", "listado_regiones", "listado_zonas", "listado_educacion",
                       "listado_pobreza_zona", "grafico_barras", "grafico_lineas",
                       "grafico_dispersion", "grafico_torta"]:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_descargas(self):
        for r in REPORTES:
            pdf = self.client.get(reverse("descargar_pdf", args=[r]))
            self.assertEqual(pdf.status_code, 200)
            self.assertTrue(pdf.content.startswith(b"%PDF"))
            xlsx = self.client.get(reverse("descargar_excel", args=[r]))
            self.assertEqual(xlsx.status_code, 200)
            self.assertTrue(xlsx.content.startswith(b"PK"))

    def test_filtro_zona(self):
        for z in ["Todas", "Urbano", "Rural"]:
            self.assertEqual(self.client.get(reverse("grafico_torta"), {"zona": z}).status_code, 200)
            self.assertEqual(self.client.get(reverse("descargar_pdf", args=["pobreza_zona"]), {"zona": z}).status_code, 200)
