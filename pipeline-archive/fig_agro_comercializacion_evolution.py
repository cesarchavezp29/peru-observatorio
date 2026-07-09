"""
fig_agro_comercializacion_evolution.py - Destino de la produccion agricola 2011-2025
=====================================================================================
Modulo 22 (Produccion agricola), llave HOGAR-ITEM (1 fila por hogar x producto).
Valor del item: p21002b=venta, p21002f=autoconsumo (consumo del hogar), p21002n=total.
Cuota nacional = Sum(factor07*venta) / Sum(factor07*total) e idem autoconsumo. El
modulo agro NO trae factor07 -> se carga de Sumaria por llave-hogar.

COMPARABILIDAD: el bloque de destino detallado (p21002b..t) recien existe 2011+;
2004-2006 traen otra estructura (p21002a/b/c). Por eso la serie arranca en 2011.
(Verificado en variable-labels 2011 vs 2025: identicas.)

Una figura, un eje, paleta figstyle.
Run: python fig_agro_comercializacion_evolution.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "08_agro"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


def L(folder, mod, year):
    p = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


rows = []
for y in ec.years():
    if y <= 2006:
        continue  # estructura de destino distinta
    m22 = L("prod_agricola", "22", y); su = L("sumaria", "34", y)
    if m22 is None or su is None or "p21002b" not in m22.columns:
        continue
    m22["hh"] = hh(m22)
    su["hh"] = hh(su); su["factor07"] = pd.to_numeric(su["factor07"], errors="coerce")
    fw = su.set_index("hh")["factor07"]
    venta = pd.to_numeric(m22["p21002b"], errors="coerce").fillna(0)
    auto = pd.to_numeric(m22["p21002f"], errors="coerce").fillna(0)
    tot = pd.to_numeric(m22["p21002n"], errors="coerce").fillna(0)
    w = m22["hh"].map(fw).fillna(0).values
    T = float(np.sum(w * tot.values))
    if T <= 0:
        continue
    rows.append({"year": y,
                 "venta": 100 * np.sum(w * venta.values) / T,
                 "autoconsumo": 100 * np.sum(w * auto.values) / T,
                 "n_hogares_agro": m22["hh"].nunique()})
    print(f"{y}: venta {rows[-1]['venta']:4.1f}%  autoconsumo {rows[-1]['autoconsumo']:4.1f}%  "
          f"({rows[-1]['n_hogares_agro']:,} hogares agro)")

panel = pd.DataFrame(rows)
panel.to_csv(DATA / "agro_comercializacion_2011_2025.csv", index=False)

fig, ax = fs.fig_ax()
ax.plot(panel.year, panel.venta, "-o", color=fs.NAVY, lw=2.4, ms=5, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ax.plot(panel.year, panel.autoconsumo, "-o", color=fs.CRANBERRY, lw=2.4, ms=5, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
fs.halo_label(ax, panel.year.iloc[-1], panel.venta.iloc[-1], f"Venta al mercado  {panel.venta.iloc[-1]:.0f}%", dx=6, dy=4, fs=9.5, color=fs.NAVY)
fs.halo_label(ax, panel.year.iloc[-1], panel.autoconsumo.iloc[-1], f"Autoconsumo del hogar  {panel.autoconsumo.iloc[-1]:.0f}%", dx=6, dy=-4, fs=9.5, color=fs.CRANBERRY)
ax.set_xlim(2010.5, 2030)
ax.set_ylim(0, max(75, panel.venta.max() * 1.15))
ax.set_xticks(range(2011, 2026, 2))
ax.set_ylabel("% del valor de la produccion agricola")
ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2011-2025 (INEI), modulo 22 (Produccion agricola) x Sumaria. Valor S/. ponderado por factor07 del hogar.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_agro_comercializacion_evolution.{e}", dpi=200, bbox_inches="tight")
print("OK -> figures/08_agro/fig_agro_comercializacion_evolution.pdf")
