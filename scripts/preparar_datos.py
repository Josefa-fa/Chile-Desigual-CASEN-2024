"""
Prepara los datos del dashboard a partir de los microdatos CASEN 2024.

Lee casen_2024.dta (1,6 GB, no se sube al repositorio), calcula los
indicadores ponderados por el factor de expansión (expr) y genera el fixture
analisis/fixtures/casen.json, que se carga con:  python manage.py loaddata casen

Uso:  python scripts/preparar_datos.py "ruta/a/casen_2024.dta"
Requiere pandas y numpy (solo para este script, no para el sitio Django).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REGIONES = {
    1: "Tarapacá", 2: "Antofagasta", 3: "Atacama", 4: "Coquimbo",
    5: "Valparaíso", 6: "O'Higgins", 7: "Maule", 8: "Biobío",
    9: "La Araucanía", 10: "Los Lagos", 11: "Aysén", 12: "Magallanes",
    13: "Metropolitana", 14: "Los Ríos", 15: "Arica y Parinacota", 16: "Ñuble",
}
ORDEN_REGIONES = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]  # norte a sur
ZONAS = {1: "Urbano", 2: "Rural"}
EDUCC = ["Sin educación formal", "Básica incompleta", "Básica completa",
         "Media incompleta", "Media completa", "Superior incompleta",
         "Superior completa"]
COLUMNAS = ["region", "area", "edad", "educc", "esc", "pobreza",
            "pobreza_multi", "ypchtotcor", "expr", "ind_hacina"]


def media_pond(d, var):
    d = d[[var, "expr"]].dropna()
    return float(np.average(d[var], weights=d["expr"])) if len(d) else 0.0


def cuantil_pond(d, var, q):
    d = d[[var, "expr"]].dropna().sort_values(var)
    acum = d["expr"].cumsum() / d["expr"].sum()
    return float(np.interp(q, acum, d[var]))


def indicadores(d):
    """Indicadores comunes de un grupo de personas."""
    return {
        "poblacion": round(float(d["expr"].sum())),
        "pobreza_ingresos": round(media_pond(d, "pobre") * 100, 2),
        "pobreza_extrema": round(media_pond(d, "pobre_extrema") * 100, 2),
        "pobreza_multidimensional": round(media_pond(d, "pobreza_multi") * 100, 2),
        "ingreso_mediano": round(cuantil_pond(d, "ypchtotcor", 0.5)),
        "escolaridad_adultos": round(media_pond(d, "esc_adulto"), 2),
    }


def gini(d):
    d = d[["ypchtotcor", "expr"]].dropna().sort_values("ypchtotcor")
    w, x = d["expr"].to_numpy(float), d["ypchtotcor"].to_numpy(float)
    p = np.concatenate([[0], np.cumsum(w) / w.sum()])
    L = np.concatenate([[0], np.cumsum(w * x) / (w * x).sum()])
    return 1 - np.sum(np.diff(p) * (L[1:] + L[:-1]))


def main(ruta):
    df = pd.read_stata(ruta, columns=COLUMNAS, convert_categoricals=False)
    print(f"{len(df):,} registros leídos")

    df["educc"] = df["educc"].replace(-88, np.nan)
    df["pobre"] = np.where(df["pobreza"].isna(), np.nan, df["pobreza"].isin([1, 2]).astype(float))
    df["pobre_extrema"] = np.where(df["pobreza"].isna(), np.nan, (df["pobreza"] == 1).astype(float))
    df["esc_adulto"] = np.where(df["edad"] >= 18, df["esc"], np.nan)

    filas = []

    contador = {}

    def agregar(modelo, **campos):
        # pk fijo por modelo: cargar el fixture dos veces no duplica registros
        contador[modelo] = contador.get(modelo, 0) + 1
        filas.append({"model": f"analisis.{modelo}", "pk": contador[modelo],
                      "fields": campos})

    # Listado 1: pobreza por región (orden norte a sur)
    for orden, cod in enumerate(ORDEN_REGIONES, start=1):
        agregar("indicadorregion", orden=orden, nombre=REGIONES[cod],
                **indicadores(df[df["region"] == cod]))

    # Listado 2: zona urbana y rural
    for cod, nombre in ZONAS.items():
        d = df[df["area"] == cod]
        hacina = d.assign(h=np.where(d["ind_hacina"] > 0, (d["ind_hacina"] >= 2), np.nan))
        agregar("indicadorzona", nombre=nombre, **indicadores(d),
                hacinamiento=round(media_pond(hacina, "h") * 100, 2))

    # Listado 3: nivel educacional de los adultos (18 años o más)
    adultos = df[df["edad"] >= 18]
    total = adultos["expr"].sum()
    for cod, nombre in enumerate(EDUCC):
        d = adultos[adultos["educc"] == cod]
        agregar("indicadoreducacion", orden=cod, nivel=nombre,
                poblacion=round(float(d["expr"].sum())),
                porcentaje_adultos=round(float(d["expr"].sum() / total * 100), 2),
                ingreso_mediano=round(cuantil_pond(d, "ypchtotcor", 0.5)),
                ingreso_medio=round(media_pond(d, "ypchtotcor")),
                pobreza_ingresos=round(media_pond(d, "pobre") * 100, 2))

    # Deciles de ingreso per cápita (para la curva de Lorenz)
    d = df[["ypchtotcor", "expr"]].dropna().sort_values("ypchtotcor")
    acum = d["expr"].cumsum() / d["expr"].sum()
    d["decil"] = np.minimum(np.ceil(acum * 10 - 1e-9), 10).astype(int).clip(lower=1)
    total_ing = float((d["ypchtotcor"] * d["expr"]).sum())
    for dec in range(1, 11):
        g = d[d["decil"] == dec]
        agregar("ingresodecil", decil=dec,
                ingreso_medio=round(media_pond(g, "ypchtotcor")),
                participacion=round(float((g["ypchtotcor"] * g["expr"]).sum() / total_ing * 100), 2))

    # Indicador nacional (KPI del inicio)
    agregar("resumennacional", poblacion=round(float(df["expr"].sum())),
            registros=len(df), gini=round(gini(df), 3),
            **{k: v for k, v in indicadores(df).items() if k != "poblacion"})

    salida = Path(__file__).resolve().parent.parent / "analisis" / "fixtures" / "casen.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Fixture generado:", salida, f"({len(filas)} filas)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
