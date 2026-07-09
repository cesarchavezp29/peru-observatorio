"""
dataset_sector_flujo.py  -  Labor-market sector mobility network (2007->2011)
=============================================================================
The ENAHO panel module 500 records each worker's CIIU activity (p506r4) in the
first (2007) and last (2011) wave. Grouping CIIU to broad sectors gives a
sector origin->destination flow: who moved from, say, agriculture to services.
Weighted by the 2007 person factor.

Output (datasets/):
  empleo_sector_flujo_2007_2011.csv   origen, destino, personas
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "panel" / "2011_302" / "enaho01A-2007-2011-500-panel.dta"
OUT = ROOT / "datasets" / "empleo_sector_flujo_2007_2011.csv"


def sector(ciiu) -> str | None:
    try:
        d = int(str(int(ciiu)).zfill(4)[:2])
    except (TypeError, ValueError):
        return None
    if d < 1 or d > 99:
        return None
    if d <= 3:  return "Agropecuario/Pesca"
    if d <= 9:  return "Minería"
    if d <= 33: return "Manufactura"
    if d <= 39: return "Electricidad/Agua"
    if d <= 43: return "Construcción"
    if d <= 47: return "Comercio"
    if d <= 53: return "Transporte"
    if d <= 56: return "Restaurantes/Hoteles"
    if d == 84: return "Adm. Pública"
    if d == 85: return "Educación"
    if 86 <= d <= 88: return "Salud"
    return "Otros Servicios"


def main():
    df, _ = pyreadstat.read_dta(str(SRC), encoding="latin1",
                                usecols=["p506r4_07", "p506r4_11", "fact_07"])
    df["s0"] = df["p506r4_07"].map(sector)
    df["s1"] = df["p506r4_11"].map(sector)
    df["w"] = pd.to_numeric(df["fact_07"], errors="coerce")
    d = df.dropna(subset=["s0", "s1", "w"])
    d = d[d["w"] > 0]
    print(f"workers with a sector in both waves: {len(d):,}")

    od = (d.groupby(["s0", "s1"])["w"].sum().reset_index()
          .rename(columns={"s0": "origen", "s1": "destino", "w": "personas"}))
    od["personas"] = od["personas"].round().astype(int)
    od = od[od["personas"] > 0].sort_values("personas", ascending=False)

    OUT.parent.mkdir(exist_ok=True)
    od.to_csv(OUT, index=False)
    stay = od[od.origen == od.destino]["personas"].sum()
    move = od[od.origen != od.destino]["personas"].sum()
    print(f"wrote {OUT.name}: {len(od)} flows; stayed {stay:,} ({100*stay/(stay+move):.0f}%), "
          f"changed sector {move:,}")
    print("top sector changes:")
    for _, r in od[od.origen != od.destino].head(8).iterrows():
        print(f"  {r['origen']:>20} -> {r['destino']:<20} {r['personas']:>10,}")


if __name__ == "__main__":
    main()
