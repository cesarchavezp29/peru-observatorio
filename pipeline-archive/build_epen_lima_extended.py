"""
build_epen_lima_extended.py
===========================
Serie Lima Metropolitana EMPALMADA 2001-2026: microdatos EPE (2001-2022, reproduce
INEI/BCRP a 0.00pp) + serie oficial INEI/BCRP (2022-2026, EPE discontinuada en 2022).
Indicadores con contraparte BCRP trimestral: desempleo total/H/M/edad, ingreso nominal.

In:  datasets/epen_lima_empleo_trim_2001_2022.csv (micro), datasets/_bcrp_lima_2026.csv (BCRP)
Out: datasets/epen_lima_series_2001_2026.csv  (ym, indicador..., fuente)
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MIC = ROOT / "datasets" / "epen_lima_empleo_trim_2001_2022.csv"
BCRP = ROOT / "datasets" / "_bcrp_lima_2026.csv"
OUT = ROOT / "datasets" / "epen_lima_series_2001_2026.csv"
SPLICE = 202209
# micro col -> bcrp col
MAP = {"tasa_desempleo": "des_total_bcrp", "tasa_desempleo_h": "des_h",
       "tasa_desempleo_m": "des_m", "tasa_desempleo_joven": "des_joven",
       "tasa_desempleo_adulto": "des_adulto", "tasa_desempleo_mayor": "des_mayor"}


def endkey(ts):
    y, m = ts // 100, ts % 100; em = m + 2; ey = y
    if em > 12: em -= 12; ey += 1
    return ey * 100 + em


def main():
    mic = pd.read_csv(MIC); mic["ym"] = mic["trim_start"].apply(endkey)
    b = pd.read_csv(BCRP)
    b["des_total_bcrp"] = b["des_h"]  # placeholder, replaced below by the total series file
    # bring the validated total from the dedicated extended file if present
    tot = pd.read_csv(ROOT / "datasets" / "epen_lima_desempleo_2001_2026.csv")[["ym", "tasa_desempleo"]]
    rows = []
    bm = b.set_index("ym")
    for ym in sorted(set(mic["ym"]) | set(b["ym"])):
        if ym < mic["ym"].min():
            continue
        rec = {"ym": int(ym)}
        if ym <= SPLICE and ym in set(mic["ym"]):
            r = mic[mic["ym"] == ym].iloc[0]
            for mc in MAP:
                rec[mc.replace("tasa_", "")] = r[mc]
            rec["ingreso"] = r["ing_lab_prom"]
            rec["fuente"] = "micro_EPE"
        elif ym > SPLICE and ym in bm.index:
            br = bm.loc[ym]
            rec["desempleo"] = br.get("des_h")  # filled below from total file
            rec["desempleo_h"] = br["des_h"]; rec["desempleo_m"] = br["des_m"]
            rec["desempleo_joven"] = br["des_joven"]; rec["desempleo_adulto"] = br["des_adulto"]
            rec["desempleo_mayor"] = br["des_mayor"]; rec["ingreso"] = br["ingreso"]
            rec["fuente"] = "BCRP_oficial"
        else:
            continue
        rows.append(rec)
    d = pd.DataFrame(rows)
    d = d.merge(tot.rename(columns={"tasa_desempleo": "desempleo_total"}), on="ym", how="left")
    d = d.sort_values("ym")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} | {len(d)} trimestres | span {int(d.ym.min())}-{int(d.ym.max())}")
    print(f"  micro: {(d.fuente=='micro_EPE').sum()}  BCRP: {(d.fuente=='BCRP_oficial').sum()}")


if __name__ == "__main__":
    main()
