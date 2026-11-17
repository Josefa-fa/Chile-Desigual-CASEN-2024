import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")  # Dibujar sin abrir una ventana gráfica
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.http import HttpResponse
from django.shortcuts import render

from .models import (IndicadorEducacion, IndicadorRegion, IndicadorZona,
                     IndicadorSunburst, IngresoDecil, ResumenNacional)

AZUL = "#244765"
AZUL_OSCURO = "#17324d"
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


def _formatear_numero_cl(valor):
    # Formato chileno para visualización en PDF (miles con punto, decimales con coma)
    if valor is None:
        return "-"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    if isinstance(valor, float):
        return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def _obtener_datos_pobreza_zona(zona_param):
    # Fuente única de datos para el 4° gráfico dinámico y el 4° reporte
    zona = zona_param if zona_param in ["Todas", "Urbano", "Rural"] else "Todas"
    datos = IndicadorSunburst.objects.all()

    if zona in ["Urbano", "Rural"]:
        datos = datos.filter(zona=zona)

    categorias = [
        "Pobreza extrema",
        "Pobreza no extrema",
        "No pobre",
    ]

    filas = []
    total_hogares = sum(
        dato.hogares_muestra
        for dato in datos
        if dato.situacion_pobreza in categorias
    )

    for categoria in categorias:
        cantidad = sum(
            dato.hogares_muestra
            for dato in datos
            if dato.situacion_pobreza == categoria
        )
        porcentaje = round((cantidad / total_hogares) * 100, 1) if total_hogares > 0 else 0.0
        filas.append({
            "categoria": categoria,
            "cantidad": cantidad,
            "porcentaje": porcentaje,
        })

    return zona, filas, total_hogares


def inicio(request):
    # Indicadores nacionales guardados en la base de datos
    contexto = {"resumen": ResumenNacional.objects.first()}
    return render(request, "analisis/inicio.html", contexto)


# ---------------------------------------------------------------- Reportes (Listados)

def listado_regiones(request):
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
        "razon": round(superior.ingreso_mediano / sin_formal.ingreso_mediano, 1),
        "sin_formal": sin_formal,
        "superior": superior,
    }
    return render(request, "analisis/listado_educacion.html", contexto)


def listado_pobreza_zona(request):
    zona_param = request.GET.get("zona", "Todas")
    zona, filas, total_hogares = _obtener_datos_pobreza_zona(zona_param)

    pobreza_total_pct = 0.0
    predominante = None
    if total_hogares > 0:
        pobreza_total_pct = round(filas[0]["porcentaje"] + filas[1]["porcentaje"], 1)
        predominante = max(filas, key=lambda f: f["cantidad"])

    contexto = {
        "zona": zona,
        "filas": filas,
        "total_hogares": total_hogares,
        "pobreza_total_pct": pobreza_total_pct,
        "predominante": predominante,
    }
    return render(request, "analisis/listado_pobreza_zona.html", contexto)


# ---------------------------------------------------------------- Construcción unificada para PDF / Excel

def _construir_datos_reporte(reporte, request):
    if reporte == "regiones":
        regiones = list(IndicadorRegion.objects.all())
        nacional = ResumenNacional.objects.first()
        mayor = max(regiones, key=lambda r: r.pobreza_ingresos)
        menor = min(regiones, key=lambda r: r.pobreza_ingresos)

        titulo = "Pobreza por región (CASEN 2024)"
        filtro_texto = None
        explicacion = (
            f"Esta tabla muestra, para cada una de las 16 regiones (ordenadas de norte a sur), "
            f"la población estimada, el porcentaje de personas en pobreza por ingresos, en pobreza "
            f"extrema y en pobreza multidimensional, el ingreso per cápita mediano del hogar y los "
            f"años de escolaridad promedio de los adultos. La región con mayor pobreza por ingresos "
            f"es {mayor.nombre} ({_formatear_numero_cl(mayor.pobreza_ingresos)}%) y la de menor pobreza es "
            f"{menor.nombre} ({_formatear_numero_cl(menor.pobreza_ingresos)}%); el promedio nacional es "
            f"{_formatear_numero_cl(nacional.pobreza_ingresos)}%."
        )
        fuente = (
            "Fuente: CASEN 2024, Ministerio de Desarrollo Social y Familia. "
            "Valores ponderados por el factor de expansión."
        )
        encabezados = [
            "Región",
            "Población estimada",
            "Pobreza por ingresos (%)",
            "Pobreza extrema (%)",
            "Pobreza multidimensional (%)",
            "Ingreso mediano ($)",
            "Escolaridad adultos (años)",
        ]
        filas = [
            [
                r.nombre,
                int(r.poblacion),
                round(float(r.pobreza_ingresos), 1),
                round(float(r.pobreza_extrema), 1),
                round(float(r.pobreza_multidimensional), 1),
                int(r.ingreso_mediano),
                round(float(r.escolaridad_adultos), 1),
            ]
            for r in regiones
        ]
        fila_total = [
            "Chile",
            int(nacional.poblacion),
            round(float(nacional.pobreza_ingresos), 1),
            round(float(nacional.pobreza_extrema), 1),
            round(float(nacional.pobreza_multidimensional), 1),
            int(nacional.ingreso_mediano),
            round(float(nacional.escolaridad_adultos), 1),
        ]
        return {
            "nombre_archivo": "reporte_pobreza_regiones",
            "titulo": titulo,
            "filtro_texto": filtro_texto,
            "explicacion": explicacion,
            "fuente": fuente,
            "encabezados": encabezados,
            "filas": filas,
            "fila_total": fila_total,
        }

    if reporte == "zonas":
        zonas = list(IndicadorZona.objects.all())
        urbano = next(z for z in zonas if z.nombre == "Urbano")
        rural = next(z for z in zonas if z.nombre == "Rural")
        brecha_ing = round(rural.pobreza_ingresos - urbano.pobreza_ingresos, 1)
        brecha_multi = round(rural.pobreza_multidimensional - urbano.pobreza_multidimensional, 1)
        brecha_med = int(rural.ingreso_mediano - urbano.ingreso_mediano)
        brecha_esc = round(rural.escolaridad_adultos - urbano.escolaridad_adultos, 1)

        titulo = "Pobreza urbana y rural (CASEN 2024)"
        filtro_texto = None
        explicacion = (
            f"Esta tabla compara las zonas urbana y rural del país: población estimada, tasas de "
            f"pobreza por ingresos, extrema y multidimensional, ingreso per cápita mediano, "
            f"escolaridad de los adultos y porcentaje de personas que viven en hogares con "
            f"hacinamiento. La última fila muestra la brecha (rural menos urbano): la pobreza por "
            f"ingresos rural supera a la urbana en {_formatear_numero_cl(brecha_ing)} puntos porcentuales."
        )
        fuente = (
            "pp = puntos porcentuales. Fuente: CASEN 2024. "
            "Valores ponderados por el factor de expansión."
        )
        encabezados = [
            "Zona",
            "Población estimada",
            "Pobreza por ingresos (%)",
            "Pobreza extrema (%)",
            "Pobreza multidimensional (%)",
            "Ingreso mediano ($)",
            "Escolaridad adultos (años)",
            "Hacinamiento (%)",
        ]
        filas = [
            [
                z.nombre,
                int(z.poblacion),
                round(float(z.pobreza_ingresos), 1),
                round(float(z.pobreza_extrema), 1),
                round(float(z.pobreza_multidimensional), 1),
                int(z.ingreso_mediano),
                round(float(z.escolaridad_adultos), 1),
                round(float(z.hacinamiento), 1),
            ]
            for z in zonas
        ]
        fila_total = [
            "Brecha (rural - urbano)",
            None,
            brecha_ing,
            None,
            brecha_multi,
            brecha_med,
            brecha_esc,
            None,
        ]
        return {
            "nombre_archivo": "reporte_pobreza_zonas",
            "titulo": titulo,
            "filtro_texto": filtro_texto,
            "explicacion": explicacion,
            "fuente": fuente,
            "encabezados": encabezados,
            "filas": filas,
            "fila_total": fila_total,
        }

    if reporte == "educacion":
        niveles = list(IndicadorEducacion.objects.all())
        sin_formal = niveles[0]
        superior = niveles[-1]
        razon = round(superior.ingreso_mediano / sin_formal.ingreso_mediano, 1)

        titulo = "Educación e ingresos (CASEN 2024)"
        filtro_texto = None
        explicacion = (
            f"Esta tabla agrupa a las personas de 18 años o más según su nivel educacional y "
            f"muestra cuántas son, qué porcentaje de los adultos representan, su ingreso per cápita "
            f"(mediano y medio) y su tasa de pobreza por ingresos. Las personas con educación "
            f"superior completa tienen un ingreso mediano {_formatear_numero_cl(razon)} veces el de quienes no tienen "
            f"educación formal ({_formatear_numero_cl(superior.ingreso_mediano)} frente a {_formatear_numero_cl(sin_formal.ingreso_mediano)} "
            f"pesos al mes)."
        )
        fuente = (
            "El ingreso es el ingreso total per cápita del hogar de cada persona. "
            "Fuente: CASEN 2024."
        )
        encabezados = [
            "Nivel educacional",
            "Adultos estimados",
            "% de los adultos",
            "Ingreso mediano ($)",
            "Ingreso medio ($)",
            "Pobreza por ingresos (%)",
        ]
        filas = [
            [
                n.nivel,
                int(n.poblacion),
                round(float(n.porcentaje_adultos), 1),
                int(n.ingreso_mediano),
                int(n.ingreso_medio),
                round(float(n.pobreza_ingresos), 1),
            ]
            for n in niveles
        ]
        return {
            "nombre_archivo": "reporte_educacion_ingresos",
            "titulo": titulo,
            "filtro_texto": filtro_texto,
            "explicacion": explicacion,
            "fuente": fuente,
            "encabezados": encabezados,
            "filas": filas,
            "fila_total": None,
        }

    if reporte == "pobreza_zona":
        zona_param = request.GET.get("zona", "Todas")
        zona, datos_zona, total_hogares = _obtener_datos_pobreza_zona(zona_param)
        etiqueta_zona = "Todas las zonas" if zona == "Todas" else f"Zona {zona}"
        pobreza_total = round(datos_zona[0]["porcentaje"] + datos_zona[1]["porcentaje"], 1) if total_hogares > 0 else 0.0
        predominante = max(datos_zona, key=lambda f: f["cantidad"])

        titulo = f"Situación de pobreza según zona - {etiqueta_zona}"
        filtro_texto = f"Filtro aplicado (Zona): {etiqueta_zona}"
        explicacion = (
            f"Origen y variables: Los datos provienen de los microdatos de hogares encuestados "
            f"en CASEN 2024 (hogares agrupados por zona y situación de pobreza), utilizando las variables Zona "
            f"(Urbano/Rural), Situación de pobreza por ingresos y Cantidad de hogares de la muestra. "
            f"Cálculos aplicados: Se filtran los registros según la zona seleccionada ({etiqueta_zona}), "
            f"se agrupan y suman los hogares por categoría de pobreza y se calcula su participación "
            f"porcentual sobre el total de {_formatear_numero_cl(total_hogares)} hogares encuestados."
        )
        if total_hogares > 0:
            explicacion += (
                f" Interpretación: En esta selección, la categoría predominante es "
                f"{predominante['categoria']} ({_formatear_numero_cl(predominante['porcentaje'])}%), "
                f"mientras que el {_formatear_numero_cl(pobreza_total)}% de los hogares de la muestra "
                f"se encuentra en situación de pobreza por ingresos (extrema o no extrema)."
            )
        else:
            explicacion += " No existen registros disponibles para la selección actual."

        fuente = (
            "Fuente: CASEN 2024. Elaboración propia a partir de hogares encuestados "
            "(valores muestrales sin factor de expansión)."
        )
        encabezados = [
            "Situación de pobreza",
            "Hogares en la muestra",
            "Porcentaje de la muestra (%)",
        ]
        filas = [
            [
                item["categoria"],
                int(item["cantidad"]),
                round(float(item["porcentaje"]), 1),
            ]
            for item in datos_zona
        ]
        fila_total = [
            "Total hogares encuestados",
            int(total_hogares),
            100.0 if total_hogares > 0 else 0.0,
        ]
        return {
            "nombre_archivo": f"reporte_pobreza_zona_{zona.lower()}",
            "titulo": titulo,
            "filtro_texto": filtro_texto,
            "explicacion": explicacion,
            "fuente": fuente,
            "encabezados": encabezados,
            "filas": filas,
            "fila_total": fila_total,
        }

    return None


def descargar_pdf(request, reporte):
    datos = _construir_datos_reporte(reporte, request)
    if not datos:
        return HttpResponse("Reporte no encontrado", status=404)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloReporte",
        parent=estilos["Heading1"],
        fontSize=15,
        textColor=colors.HexColor(AZUL_OSCURO),
        spaceAfter=6,
    )
    estilo_filtro = ParagraphStyle(
        "FiltroReporte",
        parent=estilos["Normal"],
        fontSize=10,
        textColor=colors.HexColor(AZUL),
        spaceAfter=8,
    )
    estilo_texto = ParagraphStyle(
        "TextoReporte",
        parent=estilos["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#243447"),
        spaceAfter=12,
    )
    estilo_fuente = ParagraphStyle(
        "FuenteReporte",
        parent=estilos["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#6c757d"),
        spaceBefore=10,
    )
    estilo_th = ParagraphStyle(
        "ThReporte",
        parent=estilos["Normal"],
        fontSize=8.5,
        leading=10,
        textColor=colors.white,
        alignment=1,  # Centrado
    )

    elementos = [Paragraph(datos["titulo"], estilo_titulo)]
    if datos["filtro_texto"]:
        elementos.append(Paragraph(f"<b>{datos['filtro_texto']}</b>", estilo_filtro))
    elementos.append(Paragraph(datos["explicacion"], estilo_texto))

    # Construir tabla con encabezados envueltos en Paragraph para evitar cortes
    tabla_data = [[Paragraph(f"<b>{h}</b>", estilo_th) for h in datos["encabezados"]]]

    for fila in datos["filas"]:
        fila_formateada = [
            fila[0] if idx == 0 else _formatear_numero_cl(val)
            for idx, val in enumerate(fila)
        ]
        tabla_data.append(fila_formateada)

    if datos["fila_total"]:
        total_formateado = [
            datos["fila_total"][0] if idx == 0 else _formatear_numero_cl(val)
            for idx, val in enumerate(datos["fila_total"])
        ]
        tabla_data.append(total_formateado)

    n_cols = len(datos["encabezados"])
    ancho_disponible = landscape(letter)[0] - 60
    ancho_primera_col = 145 if n_cols >= 6 else 220
    ancho_otras = (ancho_disponible - ancho_primera_col) / (n_cols - 1)
    col_widths = [ancho_primera_col] + [ancho_otras] * (n_cols - 1)

    tabla = Table(tabla_data, colWidths=col_widths, repeatRows=1)

    estilos_tabla = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL_OSCURO)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
    ]

    if datos["fila_total"]:
        estilos_tabla.extend([
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#dee2e6")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ])

    tabla.setStyle(TableStyle(estilos_tabla))
    elementos.append(tabla)
    elementos.append(Paragraph(datos["fuente"], estilo_fuente))

    doc.build(elementos)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{datos["nombre_archivo"]}.pdf"'
    return response


def descargar_excel(request, reporte):
    datos = _construir_datos_reporte(reporte, request)
    if not datos:
        return HttpResponse("Reporte no encontrado", status=404)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte CASEN 2024"

    # Título y filtro
    ws.cell(row=1, column=1, value=datos["titulo"]).font = Font(bold=True, size=13, color="17324D")
    fila_inicio_tabla = 3
    if datos["filtro_texto"]:
        ws.cell(row=2, column=1, value=datos["filtro_texto"]).font = Font(italic=True, size=10, color="244765")
        fila_inicio_tabla = 4

    # Encabezados
    fill_header = PatternFill(start_color="17324D", end_color="17324D", fill_type="solid")
    font_header = Font(bold=True, color="FFFFFF", size=10)

    for col_idx, header in enumerate(datos["encabezados"], start=1):
        celda = ws.cell(row=fila_inicio_tabla, column=col_idx, value=header)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Filas de datos (valores numéricos conservados como int/float)
    fila_actual = fila_inicio_tabla + 1
    for fila in datos["filas"]:
        for col_idx, valor in enumerate(fila, start=1):
            celda = ws.cell(row=fila_actual, column=col_idx, value=valor)
            if isinstance(valor, int):
                celda.number_format = "#,##0"
            elif isinstance(valor, float):
                celda.number_format = "0.0"
        fila_actual += 1

    # Fila total / brecha si existe
    if datos["fila_total"]:
        fill_total = PatternFill(start_color="DEE2E6", end_color="DEE2E6", fill_type="solid")
        font_total = Font(bold=True, size=10)
        for col_idx, valor in enumerate(datos["fila_total"], start=1):
            celda = ws.cell(row=fila_actual, column=col_idx, value=valor)
            celda.fill = fill_total
            celda.font = font_total
            if isinstance(valor, int):
                celda.number_format = "#,##0"
            elif isinstance(valor, float):
                celda.number_format = "0.0"

    # Ajustar anchos de columna
    for col_idx, header in enumerate(datos["encabezados"], start=1):
        letra_col = get_column_letter(col_idx)
        max_len = len(str(header))
        for r in range(fila_inicio_tabla + 1, fila_actual + 1):
            val = ws.cell(row=r, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[letra_col].width = max_len + 5

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{datos["nombre_archivo"]}.xlsx"'
    return response


# ---------------------------------------------------------------- Gráficos

def grafico_barras(request):
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


def grafico_torta(request):
    zona_param = request.GET.get("zona", "Todas")
    zona, filas, total_hogares = _obtener_datos_pobreza_zona(zona_param)

    categorias = [item["categoria"] for item in filas]
    cantidades = [item["cantidad"] for item in filas]

    colores = [
        "#df7779",  # Rojo suave
        "#e9ae70",  # Naranjo suave
        "#7196b5",  # Azul suave
    ]

    figura, eje = plt.subplots(figsize=(9, 5.5))

    if total_hogares > 0:
        porciones, textos, porcentajes = eje.pie(
            cantidades,
            labels=None,
            autopct="%1.1f%%",
            startangle=90,
            colors=colores,
            pctdistance=0.68,
            wedgeprops={
                "edgecolor": "white",
                "linewidth": 2,
            },
            textprops={
                "fontsize": 11,
                "fontweight": "bold",
                "color": "#233344",
            },
        )

        etiquetas = [
            f"{categoria}: {cantidad:,} hogares".replace(",", ".")
            for categoria, cantidad in zip(categorias, cantidades)
        ]

        eje.legend(
            porciones,
            etiquetas,
            title="Situación de pobreza",
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            fontsize=10,
            frameon=False,
        )

        etiqueta_titulo = "Todas las zonas" if zona == "Todas" else f"Zona {zona}"
        eje.set_title(f"Situación de pobreza - {etiqueta_titulo}")
        eje.axis("equal")
    else:
        eje.text(
            0.5, 0.5,
            "No hay datos disponibles para la selección actual",
            ha="center",
            va="center",
        )
        eje.axis("off")

    figura.tight_layout()

    contexto = {
        "grafico": figura_a_base64(figura),
        "zona": zona,
        "total_hogares": total_hogares,
    }

    return render(request, "analisis/grafico_torta.html", contexto)