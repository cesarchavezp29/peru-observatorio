"""
fig_agro_productos.py - Que cultiva y cria el Peru (M22 + M26 + diccionario)
=============================================================================
Modulos agropecuarios 22 (produccion agricola) y 26 (produccion pecuaria), llave
ITEM = conglome+vivienda+hogar+codperso+pNNNNa. El codigo de producto/especie
(p2100b / p2500b) se traduce con el DICCIONARIO INEI que viaja en el zip del modulo
22: enaho_tabla_agropecuario.dta (372 productos, codigo->nombre).

Universo: solo hogares productores (~10 mil de 33,702). Se cuenta el numero de
HOGARES (dedup hh x producto) que cultiva/cria cada producto, ponderado por factor07
de Sumaria (los modulos agro no traen peso). Resultado en miles de hogares.

Run: python fig_agro_productos.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, pyreadstat, matplotlib.pyplot as plt
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "08_agro"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025


def rd(p):
    df, _ = pyreadstat.read_dta(str(p), encoding="latin1"); df.columns = [c.lower() for c in df.columns]
    return df


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


# diccionario codigo -> nombre
import unicodedata
def deaccent(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
dic = rd(RAW / "prod_agricola" / "enaho_tabla_agropecuario.dta")
cmap = {int(c): deaccent(p).strip().title() for c, p in zip(dic["codigo"], dic["producto"])}

# peso del hogar desde Sumaria
su = pd.read_stata(RAW / "sumaria" / f"enaho-{YEAR}-34.dta", convert_categoricals=False)
su.columns = [c.lower() for c in su.columns]; su["hh"] = hh(su)
w = su.set_index("hh")["factor07"]


def top_products(folder, mod, codecol, n=10):
    d = rd(RAW / folder / f"enaho-{YEAR}-{mod}.dta"); d["hh"] = hh(d)
    d["code"] = pd.to_numeric(d[codecol], errors="coerce")
    d = d.dropna(subset=["code"]); d["code"] = d["code"].astype(int)
    d = d.drop_duplicates(["hh", "code"])          # un hogar cuenta una vez por producto
    d["fw"] = d["hh"].map(w)
    g = d.dropna(subset=["fw"]).groupby("code")["fw"].sum().sort_values(ascending=False)
    out = g.head(n).rename(index=cmap) / 1000        # miles de hogares
    n_hh = d.dropna(subset=["fw"]).drop_duplicates("hh")["fw"].sum() / 1000
    return out, n_hh


crops, n_agric = top_products("prod_agricola", "22", "p2100b")
animals, n_pec = top_products("prod_pecuaria", "26", "p2500b")
crops.to_csv(DATA / "agro_top_cultivos_2025.csv")
animals.to_csv(DATA / "agro_top_especies_2025.csv")
print("hogares agricolas (miles):", round(n_agric, 0), " pecuarios (miles):", round(n_pec, 0))
print("\nCULTIVOS:\n", crops.round(0))
print("\nESPECIES:\n", animals.round(0))

SRC = ("Fuente: ENAHO Modulos 22 y 26 (INEI) 2025, codigos traducidos con enaho_tabla_agropecuario.dta. "
       "Hogares productores; ponderado por factor07 de Sumaria.")


def barchart(ser, title, name):
    ser = ser.sort_values()
    fig, ax = fs.fig_ax(10.5, 6.6)
    ax.barh(range(len(ser)), ser.values, color=fs.NAVY, edgecolor="white")
    for i, v in enumerate(ser.values):
        ax.text(v + ser.max() * 0.01, i, f"{v:.0f}", va="center", fontsize=9, fontweight="semibold")
    ax.set_yticks(range(len(ser))); ax.set_yticklabels(ser.index, fontsize=9.5)
    ax.set_xlabel("Miles de hogares productores"); ax.set_xlim(0, ser.max() * 1.16)
    ax.grid(axis="y", alpha=0); ax.set_title(title, loc="left")
    fs.source(fig, SRC); fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{e}", dpi=140, bbox_inches="tight")
    print(f"OK -> figures/08_agro/{name}.pdf")


barchart(crops, f"Que cultiva el Peru rural: {n_agric:.1f} mil hogares agricolas - 2025", "fig_agro_cultivos")
barchart(animals, f"Que cria el Peru rural: {n_pec:.1f} mil hogares pecuarios - 2025", "fig_agro_crianzas")
