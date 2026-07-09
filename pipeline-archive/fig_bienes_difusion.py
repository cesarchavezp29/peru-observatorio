"""
fig_bienes_difusion.py - Difusion de bienes durables en el hogar 2004-2025 (M18 x M34)
======================================================================================
Modulo 18 (Equipamiento), llave HOGAR-ITEM (p612n=codigo bien, p612=tiene 1/2).
Para cada anio: pivote item->hogar, union 1:1 a Sumaria por factor07, y % nacional
ponderado de hogares que poseen cada bien. Curvas de difusion tecnologica.
Una sola figura, un solo eje, paleta unica figstyle (<=6 series).
Run: python fig_bienes_difusion.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "11_consumo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"

# El codigo p612n del bien CAMBIA con el rediseno ENAHO 2007-2010 (verificado en los
# cuestionarios CED-612 de cada zip: 2004/2006 = esquema VIEJO, 2011-2025 = NUEVO).
# Ver docs/NOTES_m18_codigos.md. Por eso usamos el codigo POR ESQUEMA, no uno fijo.
#   nombre -> (codigo_viejo[2004-2006], codigo_nuevo[2011-2025], color)
# NOTA (verificado 2026-06-15): "Horno microondas" (cod 12 viejo / 14 nuevo) se EXCLUYE.
# Su serie tiene un quiebre anomalo: cae 18%(2020)->14%(2021) en un solo ano y se queda
# plana, mientras refrigeradora y computadora NO caen ese ano. Una baja de 5pp especifica
# del microondas no es creible como tenencia real (los bienes durables no se "des-poseen").
# Codigo estable (value-labels 14=microondas 2013-2025), asi que es un problema de captura
# 2021, no de codigo. Ver docs/INCONSISTENCIES.md. Los 4 bienes mostrados tienen alza neta.
GOODS = {
    "Refrigeradora":             (4, 12, fs.PALETTE[0]),
    "Computadora/laptop":        (20, 7, fs.PALETTE[1]),
    "Lavadora de ropa":          (8, 13, fs.PALETTE[2]),
    "Auto/camioneta particular": (15, 17, fs.PALETTE[3]),
}


def code_for(name, year):
    old, new, _ = GOODS[name]
    return old if year <= 2006 else new


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
    m18 = L("equipamiento_hogar", "18", y); su = L("sumaria", "34", y)
    if m18 is None or su is None or "p612n" not in m18.columns:
        continue
    m18["hh"] = hh(m18)
    m18["code"] = pd.to_numeric(m18["p612n"], errors="coerce")
    m18["tiene"] = (pd.to_numeric(m18["p612"], errors="coerce") == 1).astype(float)
    piv = m18.pivot_table(index="hh", columns="code", values="tiene", aggfunc="max")
    su["hh"] = hh(su); su["factor07"] = pd.to_numeric(su["factor07"], errors="coerce")
    d = su[["hh", "factor07"]].merge(piv, on="hh", how="left")
    w = d["factor07"].values
    rec = {"year": y}
    for name in GOODS:
        c = code_for(name, y)
        if c in d.columns:
            v = d[c].fillna(0).values
            rec[name] = 100 * np.average(v, weights=w)
    rows.append(rec)
    print(f"{y}: " + "  ".join(f"{n[:6]} {rec.get(n, float('nan')):.0f}%" for n in GOODS))

panel = pd.DataFrame(rows).set_index("year")
panel.to_csv(DATA / "bienes_durables_difusion_2004_2025.csv")

fig, ax = fs.fig_ax(w=10.5, h=6.4)
for lab, (_, _, col) in GOODS.items():
    s = panel[lab].dropna()
    ax.plot(s.index, s.values, "-o", color=col, lw=2.2, ms=4, mfc="white", mec=col, mew=1.4, zorder=4)
    fs.halo_label(ax, s.index[-1], s.values[-1], f"{lab}  {s.values[-1]:.0f}%", dx=6, dy=-3, fs=9, color=col)
ax.set_xlim(2003.5, 2031)
ax.set_ylim(0, max(70, panel.max().max() * 1.1))
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de hogares que posee el bien")
ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 18 (Equipamiento) x Sumaria. Item pivotado a hogar, ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_bienes_difusion.{e}", dpi=200, bbox_inches="tight")
print("OK -> figures/11_consumo/fig_bienes_difusion.pdf")
