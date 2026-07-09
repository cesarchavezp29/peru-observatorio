"""
fig_mapas_departamento.py - Mapas coropleticos por DEPARTAMENTO con contexto, ENAHO 2025
=========================================================================================
La ENAHO es representativa a nivel DEPARTAMENTO. UN mapa por ARCHIVO (un-plot-por-chart).
Cada mapa: oceano Pacifico + paises vecinos (Natural Earth) como contexto, Peru coropletico
(paleta figstyle), y el VALOR de CADA uno de los 25 departamentos en su centroide.
Shapefile INEI 2025 disuelto a 2 digitos de ubigeo (cod. INEI = el de la ENAHO).

Datos: datasets/sintesis_departamento_2025.csv. Paises vecinos = Natural Earth 110m,
descargar una vez (gitignored en raw/):
  curl -sL -o raw/_geo/countries.geojson \\
    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson
Run: python fig_mapas_departamento.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.patches import Rectangle
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT / "datasets"
FIG = ROOT / "figures" / "12_mapas"; FIG.mkdir(parents=True, exist_ok=True)
SHP = Path("D:/Shining Path and Geographic/Final Results/Figures/Limite Distrital INEI 2025 CPV.shp")
GEO = ROOT / "raw" / "_geo" / "countries.geojson"
fs.use()
OCEAN = "#bcd7e6"; LAND = "#e7e4dd"; LANDEDGE = "#cdc9c0"   # azul mar / tierra calida

SEQ = LinearSegmentedColormap.from_list("seq", ["#eaf0f6", "#9fb8cf", fs.NAVY])
SEQ_R = LinearSegmentedColormap.from_list("seqr", ["#f7e6ec", "#d98aa3", fs.CRANBERRY])
MAPS = [
    ("Ingreso real pc", "Ingreso real per capita mensual (S/ 2025)", "S/", SEQ),
    ("Pobreza", "Pobreza monetaria (% de personas)", "%", SEQ_R),
    ("Educacion (anios)", "Anios de escolaridad, adultos 25+", "a", SEQ),
    ("Informalidad", "Empleo informal (% de ocupados)", "%", SEQ_R),
    ("Afiliado SIS", "Afiliacion al SIS publico (% de personas)", "%", SEQ_R),
    ("Lengua indigena", "Poblacion con lengua materna indigena (%)", "%", SEQ),
    ("Adultos 60+", "Adultos mayores de 60 anios (%)", "%", SEQ),
    ("Empleo agricola", "Empleo agricola (% de ocupados)", "%", SEQ_R),
]
CO_LABELS = {"Ecuador": (-79.4, -1.0), "Colombia": (-71.5, -0.6), "Brazil": (-70.6, -9.0),
             "Bolivia": (-68.9, -15.6), "Chile": (-69.9, -18.9)}
CO_NAME = {"Brazil": "BRASIL"}

d = pd.read_csv(DATA / "sintesis_departamento_2025.csv", dtype={"dep": str})
d["dep"] = d["dep"].str.zfill(2)
g = gpd.read_file(SHP); g["UBIGEO"] = g["UBIGEO"].astype(str).str.zfill(6); g["dep"] = g["UBIGEO"].str[:2]
names = g.groupby("dep")["DEPARTAMEN"].first().str.title()
gd = g.dissolve("dep")[["geometry"]].reset_index().merge(d, on="dep", how="left")
gd["nombre"] = gd["dep"].map(names)
gd["cx"] = gd.geometry.representative_point().x; gd["cy"] = gd.geometry.representative_point().y
co = gpd.read_file(GEO)
xmin, ymin, xmax, ymax = -82.6, -19.6, -67.2, 0.9


def fmt(v, suf):
    return f"S/{v:,.0f}" if suf == "S/" else (f"{v:.0f}%" if suf == "%" else f"{v:.1f}")


def halo(t, lw=2.4):
    t.set_path_effects([pe.withStroke(linewidth=lw, foreground="white")])


for col, title, suf, cmap in MAPS:
    vals = gd[col].dropna()
    norm = Normalize(*np.percentile(vals, [2, 98]))
    fig, ax = plt.subplots(figsize=(7.6, 8.8))
    # OCEANO: rectangulo explicito (axis('off') oculta el facecolor del eje, por eso iba blanco)
    ax.add_patch(Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, facecolor=OCEAN, edgecolor="none", zorder=0))
    co.plot(ax=ax, color=LAND, edgecolor=LANDEDGE, linewidth=0.5, zorder=1)           # vecinos
    gd.plot(ax=ax, column=col, cmap=cmap, norm=norm, edgecolor="white", linewidth=0.5,
            zorder=2, missing_kwds={"color": "#e3e3e3", "edgecolor": "0.6"})
    # etiquetas de paises vecinos + oceano
    for cn, (lx, ly) in CO_LABELS.items():
        halo(ax.text(lx, ly, CO_NAME.get(cn, cn.upper()), fontsize=8.5, color="#9aa0a6",
                     ha="center", va="center", style="italic", zorder=3), 1.8)
    halo(ax.text(-80.6, -9.5, "OCEANO\nPACIFICO", fontsize=8.5, color="#7fa8c4", ha="center",
                 va="center", style="italic", rotation=58, zorder=3, linespacing=0.9), 1.8)
    # VALOR de cada departamento en su centroide (declutter vertical para Lima/Callao)
    sub = gd.dropna(subset=[col])
    L = [{"x": cx, "y": cy, "ly": cy, "t": fmt(v, suf)}
         for cx, cy, v in zip(sub["cx"], sub["cy"], sub[col])]
    L.sort(key=lambda e: -e["y"]); sep = (ymax - ymin) * 0.032
    for k in range(1, len(L)):
        if abs(L[k]["x"] - L[k - 1]["x"]) < (xmax - xmin) * 0.07 and L[k - 1]["ly"] - L[k]["ly"] < sep:
            L[k]["ly"] = L[k - 1]["ly"] - sep
    for e in L:
        if abs(e["ly"] - e["y"]) > 1e-6:
            ax.plot([e["x"], e["x"]], [e["y"], e["ly"]], color="#777", lw=0.4, zorder=4)
        halo(ax.text(e["x"], e["ly"], e["t"], fontsize=7.3, ha="center", va="center",
                     color="#15181b", zorder=5))
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_aspect("equal"); ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.038, pad=0.01, aspect=34)
    cb.set_label({"S/": "soles/mes", "%": "%", "a": "anios"}[suf], fontsize=9.5); cb.outline.set_visible(False)
    fig.suptitle(title + "  -  por departamento, 2025", fontsize=12.5, fontweight="semibold", y=0.965)
    fs.source(fig, "Fuente: ENAHO 2025 (INEI), por departamento. Limites INEI 2025; paises Natural Earth.")
    fig.tight_layout()
    slug = col.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("+", "mas")
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"fig_mapa_{slug}.{ext}", dpi=190, bbox_inches="tight")
    plt.close(fig)
    print(f"OK -> fig_mapa_{slug}")
print("listo: 8 mapas con contexto + valores por departamento")
