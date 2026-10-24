import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # Dibujar sin abrir una ventana gráfica
import matplotlib.pyplot as plt
from django.shortcuts import render

from .models import (IndicadorEducacion, IndicadorRegion, IndicadorZona,
                     IngresoDecil, ResumenNacional)

AZUL = "#244765"
NARANJA = "#dd6b20"
ROJO = "#c53030"


def figura_a_base64(figura):
    # Convertir la imagen PNG a texto para enviarla a HTML
    buffer = BytesIO()
    figura.savefig(buffer, format="png", dpi=120)
    plt.close(figura)
    buffer.seek(0)
    grafico = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    return grafico


def inicio(request):
    # Indicadores nacionales guardados en la base de datos
    contexto = {"resumen": ResumenNacional.objects.first()}
    return render(request, "analisis/inicio.html", contexto)


# ---------------------------------------------------------------- Listados

def listado_regiones(request):
    # Consultar la tabla IndicadorRegion (ordenada de norte a sur)
    regiones = IndicadorRegion.objects.all()
    nacional = ResumenNacional.objects.first()

    mayor = max(regiones, key=lambda r: r.pobreza_ingresos)
    menor = min(regiones, key=lambda r: r.pobreza_ingresos)
    contexto = {
        "regiones": regiones,
        "nacional": nacional,
        "mayor": mayor,
        "menor": menor,
    }
    return render(request, "analisis/listado_regiones.html", contexto)


def listado_zonas(request):
    zonas = list(IndicadorZona.objects.all())
    urbano = next(z for z in zonas if z.nombre == "Urbano")
    rural = next(z for z in zonas if z.nombre == "Rural")

    # Brecha rural - urbano: se calcula en la vista y se envía a la plantilla
    brecha = {
        "pobreza_ingresos": rural.pobreza_ingresos - urbano.pobreza_ingresos,
        "pobreza_multidimensional":
            rural.pobreza_multidimensional - urbano.pobreza_multidimensional,
        "ingreso_mediano": rural.ingreso_mediano - urbano.ingreso_mediano,
        "escolaridad_adultos": rural.escolaridad_adultos - urbano.escolaridad_adultos,
    }
    contexto = {"zonas": zonas, "brecha": brecha}
    return render(request, "analisis/listado_zonas.html", contexto)


def listado_educacion(request):
    niveles = list(IndicadorEducacion.objects.all())
    sin_formal = niveles[0]
    superior = niveles[-1]
    contexto = {
        "niveles": niveles,
        # Cuántas veces es mayor el ingreso mediano con educación superior
        "razon": round(superior.ingreso_mediano / sin_formal.ingreso_mediano, 1),
        "sin_formal": sin_formal,
        "superior": superior,
    }
    return render(request, "analisis/listado_educacion.html", contexto)


# ---------------------------------------------------------------- Gráficos

def grafico_barras(request):
    # Pobreza por ingresos de cada región, de mayor a menor
    regiones = sorted(IndicadorRegion.objects.all(),
                      key=lambda r: r.pobreza_ingresos)
    nacional = ResumenNacional.objects.first()

    nombres = [r.nombre for r in regiones]
    tasas = [r.pobreza_ingresos for r in regiones]
    colores = [ROJO if t > nacional.pobreza_ingresos else AZUL for t in tasas]

    figura, eje = plt.subplots(figsize=(8, 6))
    barras = eje.barh(nombres, tasas, color=colores)
    eje.axvline(nacional.pobreza_ingresos, color="black", linestyle="--",
                linewidth=1.2,
                label=f"Promedio nacional ({nacional.pobreza_ingresos:.1f}%)".replace(".", ","))
    eje.bar_label(barras, fmt="%.1f%%", padding=3, fontsize=8)
    eje.set_title("Pobreza por ingresos según región, CASEN 2024")
    eje.set_xlabel("Población en situación de pobreza (%)")
    eje.set_xlim(0, max(tasas) + 5)
    eje.legend(loc="lower right")
    figura.tight_layout()

    contexto = {
        "grafico": figura_a_base64(figura),
        "mayor": regiones[-1],
        "menor": regiones[0],
        "nacional": nacional,
        "sobre_promedio": sum(1 for t in tasas if t > nacional.pobreza_ingresos),
    }
    return render(request, "analisis/grafico_barras.html", contexto)


def grafico_lineas(request):
    # Curva de Lorenz: porcentaje acumulado de población vs. de ingreso
    deciles = IngresoDecil.objects.all()
    poblacion = [0]
    ingreso = [0.0]
    for d in deciles:
        poblacion.append(d.decil * 10)
        ingreso.append(ingreso[-1] + d.participacion)

    figura, eje = plt.subplots(figsize=(7, 6))
    eje.plot([0, 100], [0, 100], linestyle="--", color="gray",
             label="Igualdad perfecta")
    eje.plot(poblacion, ingreso, marker="o", color=AZUL, linewidth=2,
             label="Chile (CASEN 2024)")
    eje.fill_between(poblacion, poblacion, ingreso, color=AZUL, alpha=0.12)
    eje.set_title("Curva de Lorenz del ingreso per cápita")
    eje.set_xlabel("Población acumulada (%)")
    eje.set_ylabel("Ingreso acumulado (%)")
    eje.set_xticks(range(0, 101, 10))
    eje.grid(True, alpha=0.3)
    eje.legend(loc="upper left")
    figura.tight_layout()

    contexto = {
        "grafico": figura_a_base64(figura),
        "nacional": ResumenNacional.objects.first(),
        "primeros_5": round(ingreso[5], 1),
        "ultimo_decil": deciles.last().participacion,
        "primer_decil": deciles.first().participacion,
    }
    return render(request, "analisis/grafico_lineas.html", contexto)


def grafico_dispersion(request):
    # Cada punto es una región: escolaridad de adultos vs. ingreso mediano
    regiones = IndicadorRegion.objects.all()
    escolaridad = [r.escolaridad_adultos for r in regiones]
    ingreso = [r.ingreso_mediano / 1000 for r in regiones]

    figura, eje = plt.subplots(figsize=(8, 6))
    eje.scatter(escolaridad, ingreso, color=NARANJA, s=80, edgecolor="black")
    for r, x, y in zip(regiones, escolaridad, ingreso):
        eje.annotate(r.nombre, (x, y), textcoords="offset points",
                     xytext=(6, 4), fontsize=8)
    eje.set_title("Escolaridad de los adultos e ingreso por región")
    eje.set_xlabel("Escolaridad promedio de adultos (años)")
    eje.set_ylabel("Ingreso per cápita mediano (miles de $)")
    eje.grid(True, alpha=0.3)
    figura.tight_layout()

    # Coeficiente de correlación de Pearson calculado en la vista
    n = len(escolaridad)
    mx, my = sum(escolaridad) / n, sum(ingreso) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(escolaridad, ingreso))
    sx = sum((x - mx) ** 2 for x in escolaridad) ** 0.5
    sy = sum((y - my) ** 2 for y in ingreso) ** 0.5

    contexto = {
        "grafico": figura_a_base64(figura),
        "correlacion": round(cov / (sx * sy), 2),
        "n_regiones": n,
    }
    return render(request, "analisis/grafico_dispersion.html", contexto)
