"""
build_consumo_evolution.py - Estructura del gasto del hogar (Ley de Engel) 2004-2025
====================================================================================
Composicion del gasto en los 8 GRANDES GRUPOS de la ENAHO, ano por ano, directo de
Sumaria (modulo 34) -> NO necesita los modulos-item 07-18 (Sumaria ya trae el
desglose gru<XY>hd*). Regla anti-doble-conteo: por subgrupo gru<XY>, se toman los
COMPONENTES (gru<XY>hd<N>) si existen, si no el SUBTOTAL (gru<XY>hd). Denominador =
suma de los 8 grupos (los "grandes grupos de gasto" oficiales). Participacion
agregada nacional, ponderada por factor07 (expansion del hogar):
   share_g = sum_h( factor07_h * gasto_g_h ) / sum_h( factor07_h * gasto_total8_h )

Grupos (clasificacion ENAHO):
  1 Alimentos        2 Vestido/calzado   3 Alquiler/vivienda/combustible
  4 Muebles/enseres  5 Salud             6 Transporte/comunicaciones
  7 Esparc./educ./cultura                8 Otros bienes y servicios

Salida: datasets/budget_composition_2004_2025.csv (year, grupo, codigo, share, gasto_pc_real?)
Run: python build_consumo_evolution.py
"""
from __future__ import annotations
from pathlib import Path
import re
import numpy as np, pandas as pd
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"; DATA = ROOT / "datasets"

GNAME = {1: "Alimentos", 2: "Vestido y calzado", 3: "Alquiler, vivienda y combustible",
         4: "Muebles y enseres", 5: "Salud", 6: "Transporte y comunicaciones",
         7: "Esparcimiento, educacion y cultura", 8: "Otros bienes y servicios"}


def load(year):
    p = RAW / "sumaria" / f"enaho-{year}-34.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def chosen_cols(cols):
    """Per subgroup gruXY: components (hdN) if any exist, else the subtotal (hd)."""
    sub = {}
    for c in cols:
        m = re.match(r"(gru\d\d)hd(\d*)$", c)
        if not m:
            continue
        pre, comp = m.group(1), m.group(2)
        sub.setdefault(pre, {"comp": [], "sub": None})
        if comp:
            sub[pre]["comp"].append(c)
        else:
            sub[pre]["sub"] = c
    out = []
    for pre, d in sub.items():
        out += d["comp"] if d["comp"] else ([d["sub"]] if d["sub"] else [])
    return out


rows = []
for y in ec.years():
    df = load(y)
    if df is None:
        continue
    g = df.apply(pd.to_numeric, errors="coerce")
    f = g.get("factor07")
    if f is None:
        continue
    cols = chosen_cols([c for c in df.columns if re.match(r"gru\d\dhd", c)])
    by_group = {bg: [c for c in cols if int(c[3]) == bg] for bg in range(1, 9)}
    # weighted aggregate spending per group (expanded to population of households)
    fw = f.fillna(0).values
    grp_tot = {bg: float(np.nansum(g[cc].sum(axis=1).values * fw)) for bg, cc in by_group.items()}
    denom = sum(grp_tot.values())
    if denom <= 0:
        continue
    for bg in range(1, 9):
        rows.append({"year": y, "codigo": bg, "grupo": GNAME[bg],
                     "share": 100 * grp_tot[bg] / denom})
    print(f"{y}: food share {100*grp_tot[1]/denom:5.1f}%  (denom {denom/1e6:7.1f}M)")

out = pd.DataFrame(rows)
out.to_csv(DATA / "budget_composition_2004_2025.csv", index=False)
nyr = out["year"].nunique()
print(f"\nOK -> datasets/budget_composition_2004_2025.csv  ({nyr} anios x 8 grupos)")
f0 = out[(out.year == out.year.min()) & (out.codigo == 1)]["share"].iloc[0]
f1 = out[(out.year == out.year.max()) & (out.codigo == 1)]["share"].iloc[0]
print(f"Engel: alimentos {out.year.min()} {f0:.1f}%  ->  {out.year.max()} {f1:.1f}%  ({f1-f0:+.1f} pp)")
