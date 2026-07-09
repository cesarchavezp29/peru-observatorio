"""Produce la serie mensual insignia de Lima: epen_lima_movil_modern_2022_2026
y el empalme epen_lima_movil_2001_2026.

PORTADO SIN REFACTORIZAR de build_epen_lima_modern_movil.py (computo por
trimestre movil sobre los CSV crudos EPEN, region==1, verificado contra
BCRP PN38063GM a 0.00pp) y build_epen_lima_movil_full.py (empalme con la EPE
legacy committeada). Seleccion de archivos por directorio crudo en vez del
manifest (mismo criterio: code>=774, "trim" en la etiqueta, no "nacional").

Crudos: EPEN_RAW (layout <code>_<slug>/ de perudata.epen o del workspace).
El paso de descubrimiento mensual (codigos nuevos del INEI) vive en el
workflow monthly-epen: probe + perudata.epen.download, luego este script.

Run:
  EPEN_RAW=... python pipeline/build_epen_movil.py
  EPEN_RAW=... python pipeline/build_epen_movil.py --check-against data/datasets
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
       "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
COLS = ["tasa_desempleo", "tasa_desempleo_h", "tasa_desempleo_m", "tasa_desempleo_joven",
        "tasa_desempleo_adulto", "tasa_desempleo_mayor", "tasa_actividad",
        "tasa_actividad_h", "tasa_actividad_m"]


def parse_trim(label):
    toks = re.findall(r"(ene|feb|mar|abr|may|jun|jul|ago|set|sep|oct|nov|dic)", label.lower())
    yy = re.findall(r"(\d{2})\b", label)
    if len(toks) < 3 or not yy:
        return None
    em = MES[toks[2]]
    year = 2000 + int(yy[-1])
    return year * 100 + em


def build_modern(raw: Path) -> pd.DataFrame:
    rows = []
    for d0 in sorted(raw.iterdir()):
        if not d0.is_dir() or "_" not in d0.name:
            continue
        head = d0.name.split("_", 1)
        if not head[0].isdigit():
            continue
        code = int(head[0])
        slug = head[1]
        if code < 774 or "trim" not in slug.lower() or "nacional" in slug.lower():
            continue
        ek = parse_trim(slug)
        fs = glob.glob(str(d0 / "*.csv"))
        if not fs or ek is None:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        wt = [c for c in df.columns if re.match(r"^fa_", c)]
        if not wt or "ocup300" not in df or "region" not in df:
            continue
        w = wt[0]
        for c in ["ocup300", "c207", "c208", "ingtotp", "c310", "c317a", "whorat", "p209h", w]:
            if c in df:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        g = df[(df["region"] == 1) & (df["c208"] >= 14)]

        def des(sub):
            pea = (sub[w] * sub["ocup300"].isin([1, 2])).sum()
            return round(100 * (sub[w] * (sub["ocup300"] == 2)).sum() / pea, 2) if pea else np.nan

        def act(sub):
            pet = (sub[w] * sub["ocup300"].isin([1, 2, 3, 4])).sum()
            return round(100 * (sub[w] * sub["ocup300"].isin([1, 2])).sum() / pet, 2) if pet else np.nan

        oc = g[g["ocup300"] == 1]
        perc = oc[oc.get("ingtotp", pd.Series(np.nan, index=oc.index)).notna()
                  & (oc.get("ingtotp", 0) > 0)] if "ingtotp" in g else oc.iloc[0:0]
        ing = round((perc[w] * perc["ingtotp"]).sum() / perc[w].sum()) if len(perc) and perc[w].sum() else np.nan
        if "c310" in oc and "c317a" in oc:
            small = oc["c317a"] <= 5
            informal = oc["c310"].isin([2, 4, 5, 6, 8]) | (oc["c310"].isin([1, 3, 7]) & small)
            inf = round(100 * (oc[w] * informal).sum() / oc[w].sum(), 2) if oc[w].sum() else np.nan
        else:
            inf = np.nan

        def sh(cats):
            return round(100 * (oc[w] * oc["c310"].isin(cats)).sum() / oc[w].sum(), 2) \
                if "c310" in oc and oc[w].sum() else np.nan

        if "whorat" in oc and "p209h" in oc:
            vis = (oc["whorat"] < 35) & (oc["p209h"] == 1)
            subv = round(100 * (oc[w] * vis).sum() / oc[w].sum(), 2) if oc[w].sum() else np.nan
        else:
            subv = np.nan
        if "whorat" in oc:
            hh = oc[oc["whorat"].between(1, 98)]
            sobre = round(100 * (hh[w] * (hh["whorat"] > 48)).sum() / hh[w].sum(), 2) if hh[w].sum() else np.nan
            hmed = round((hh[w] * hh["whorat"]).sum() / hh[w].sum(), 1) if hh[w].sum() else np.nan
        else:
            sobre = hmed = np.nan
        rows.append({
            "ym": ek, "code": code,
            "tasa_desempleo": des(g),
            "tasa_desempleo_h": des(g[g["c207"] == 1]), "tasa_desempleo_m": des(g[g["c207"] == 2]),
            "tasa_desempleo_joven": des(g[(g["c208"] >= 14) & (g["c208"] <= 24)]),
            "tasa_desempleo_adulto": des(g[(g["c208"] >= 25) & (g["c208"] <= 44)]),
            "tasa_desempleo_mayor": des(g[g["c208"] >= 45]),
            "tasa_actividad": act(g), "tasa_actividad_h": act(g[g["c207"] == 1]),
            "tasa_actividad_m": act(g[g["c207"] == 2]),
            "tasa_informalidad": inf, "ing_nominal": ing,
            "asalariado": sh([3]), "independiente": sh([2]), "empleador": sh([1]),
            "trab_hogar": sh([6]),
            "sub_visible": subv, "sobreempleo": sobre, "horas_medias": hmed,
        })
    return pd.DataFrame(rows).drop_duplicates("ym").sort_values("ym")


def endkey(ts):
    y, m = ts // 100, ts % 100
    em = m + 2
    ey = y
    if em > 12:
        em -= 12
        ey += 1
    return ey * 100 + em


def splice(mod: pd.DataFrame, legacy_csv: Path) -> pd.DataFrame:
    leg = pd.read_csv(legacy_csv)
    leg["ym"] = leg["trim_start"].apply(endkey)
    leg = leg[["ym"] + COLS + ["ing_lab_prom"]].rename(columns={"ing_lab_prom": "ing_nominal"})
    leg["fuente"] = "EPE legacy"
    m = mod[["ym"] + COLS + ["ing_nominal"]].copy()
    m["fuente"] = "EPEN moderno"
    m = m[m["ym"] > leg["ym"].max()]
    return pd.concat([leg, m]).drop_duplicates("ym").sort_values("ym")


def compare(newdir: Path, refdir: Path, names: list[str]) -> int:
    bad = 0
    for n in names:
        a = pd.read_csv(refdir / n)
        b = pd.read_csv(newdir / n)
        if list(a.columns) != list(b.columns) or len(a) != len(b):
            print(f"  FAIL forma {n}: ref {a.shape} vs new {b.shape}")
            bad += 1
            continue
        for c in a.columns:
            av = pd.to_numeric(a[c], errors="coerce")
            bv = pd.to_numeric(b[c], errors="coerce")
            if av.notna().any():
                dd = (av - bv).abs().max()
                if pd.notna(dd) and dd > 1e-3:
                    print(f"  FAIL {n} col {c}: max diff {dd}")
                    bad += 1
                    break
            elif not a[c].astype(str).equals(b[c].astype(str)):
                print(f"  FAIL {n} col {c}: texto difiere")
                bad += 1
                break
    print(f"comparadas {len(names)} tablas, {bad} con diferencias")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("EPEN_RAW", "peru_raw/epen"))
    if not raw.exists():
        print(f"FAIL: EPEN_RAW no existe: {raw}")
        sys.exit(1)
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS
    legacy = DATASETS / "epen_lima_empleo_trim_2001_2022.csv"

    mod = build_modern(raw)
    if mod.empty:
        print("FAIL: sin trimestres modernos")
        sys.exit(1)
    mod.to_csv(outdir / "epen_lima_movil_modern_2022_2026.csv", index=False, encoding="utf-8")
    full = splice(mod, legacy)
    full.to_csv(outdir / "epen_lima_movil_2001_2026.csv", index=False, encoding="utf-8")
    print(f"modern {len(mod)} trimestres, empalme {len(full)} ({int(full.ym.min())}-{int(full.ym.max())})")

    if a.check_against:
        bad = compare(outdir, Path(a.check_against),
                      ["epen_lima_movil_modern_2022_2026.csv", "epen_lima_movil_2001_2026.csv"])
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
