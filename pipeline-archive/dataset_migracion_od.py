"""
dataset_migracion_od.py  -  Internal migration origin->destination matrix
=========================================================================
ENAHO Module 04 asks, for each person, whether they lived in this district 5
years ago (p401f) and, if not, WHERE they lived then (p401g = ubigeo). That
gives a department origin->destination flow. Pools recent years for a robust,
weighted (factor07) inter-department migration network.

Output (datasets/):
  migracion_od_departamento.csv   origen, destino, personas  (inter-dept flows)

Run:  python dataset_migracion_od.py
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUTDIR = ROOT / "datasets"
YEARS = range(2018, 2025)   # pooled; M04 p401f/p401g available 2016+

# INEI department code -> name (ASCII)
DEP = {
    1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
    6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
    11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
    16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
    21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali",
}


def find_m04(year: int):
    for pat in (f"**/enaho-{year}-04.dta", f"**/*{year}*-04.dta"):
        hits = [h for h in glob.glob(str(RAW / pat), recursive=True)]
        if hits:
            return hits[0]
    return None


def main():
    frames = []
    for y in YEARS:
        p = find_m04(y)
        if not p:
            print(f"  [{y}] no M04 file")
            continue
        df, _ = pyreadstat.read_dta(p, encoding="latin1",
                                    usecols=["ubigeo", "p401f", "p401g", "factor07"])
        mig = df[(df["p401f"] == 2) & df["p401g"].notna() & (df["p401g"] > 0)].copy()
        mig["destino_c"] = mig["ubigeo"].astype(str).str.zfill(6).str[:2].astype(int)
        mig["origen_c"] = (mig["p401g"].astype("Int64").astype(str)
                           .str.zfill(6).str[:2].astype(int))
        mig = mig[(mig["origen_c"].between(1, 25)) & (mig["destino_c"].between(1, 25))]
        mig["anio"] = y
        frames.append(mig[["anio", "origen_c", "destino_c", "factor07"]])
        print(f"  [{y}] {len(mig):,} inter-district migrants")

    if not frames:
        raise SystemExit("no migration data")
    allm = pd.concat(frames, ignore_index=True)
    # Callao(7) folded into Lima(15) for a cleaner 24-node map, as elsewhere
    for col in ("origen_c", "destino_c"):
        allm.loc[allm[col] == 7, col] = 15
    allm = allm[allm["origen_c"] != allm["destino_c"]]   # inter-DEPARTMENT only

    od = (allm.groupby(["anio", "origen_c", "destino_c"])["factor07"].sum()
          .reset_index().rename(columns={"factor07": "personas"}))
    od["personas"] = od["personas"].round().astype(int)
    od = od[od["personas"] > 0]
    od["origen"] = od["origen_c"].map(DEP)
    od["destino"] = od["destino_c"].map(DEP)
    od = od.dropna(subset=["origen", "destino"]).sort_values(["anio", "personas"], ascending=[True, False])

    out = od[["anio", "origen", "destino", "personas"]]
    OUTDIR.mkdir(exist_ok=True)
    out.to_csv(OUTDIR / "migracion_od_departamento.csv", index=False)
    print(f"wrote migracion_od_departamento.csv: {len(out)} flows")
    print("top flows:")
    for _, r in out.head(8).iterrows():
        print(f"  {r['origen']:>14} -> {r['destino']:<14} {r['personas']:>8,}")


if __name__ == "__main__":
    main()
