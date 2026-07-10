"""Produce las comparaciones internacionales desde la API publica del Banco Mundial.

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/dataset_paises_wdi.py:
Gini (SI.POV.GINI) y pobreza comparable $6.85/dia 2017 PPP (SI.POV.UMIC),
Peru + 7 vecinos, 2000-2025. Las lineas de pobreza NACIONALES no son
comparables entre paises — por eso la vara homogenea del Banco.

Nota de refresco: el Banco revisa valores. El modo --check-against reporta
diferencias contra lo committeado — una diferencia aqui puede ser revision
legitima del Banco (se revisa a mano), no error del port.

Run:
  python pipeline/build_wdi.py
  python pipeline/build_wdi.py --check-against data/datasets
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
COUNTRIES = {"PER": "Peru", "CHL": "Chile", "COL": "Colombia", "BOL": "Bolivia",
             "ECU": "Ecuador", "BRA": "Brasil", "MEX": "Mexico", "ARG": "Argentina"}
SERIES = {
    "SI.POV.GINI": "paises_gini_tiempo_wdi.csv",
    "SI.POV.UMIC": "paises_pobreza685_wdi.csv",
}


def fetch(indicator: str) -> pd.DataFrame:
    iso = ";".join(COUNTRIES)
    url = (f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}"
           f"?format=json&per_page=2000&date=2000:2025")
    with urlopen(url, timeout=120) as r:
        data = json.load(r)[1]
    rows = [{"year": int(d["date"]), "pais": COUNTRIES[d["countryiso3code"]],
             "valor": d["value"]} for d in data if d["value"] is not None]
    df = pd.DataFrame(rows).pivot_table(index="year", columns="pais", values="valor")
    return df.round(1).reset_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS
    for ind, fname in SERIES.items():
        df = fetch(ind)
        df.to_csv(outdir / fname, index=False, encoding="utf-8")
        print(f"{fname}: {len(df)} anios")
    if a.check_against:
        bad = 0
        ref_dir = Path(a.check_against)
        for fname in SERIES.values():
            ref = pd.read_csv(ref_dir / fname)
            new = pd.read_csv(outdir / fname)
            if list(ref.columns) != list(new.columns):
                print(f"  FAIL columnas {fname}")
                bad += 1
                continue
            m = ref.merge(new, on="year", suffixes=("_ref", "_new"), how="outer")
            for c in ref.columns:
                if c == "year":
                    continue
                d = (m[f"{c}_ref"] - m[f"{c}_new"]).abs().max()
                if pd.notna(d) and d > 0.05:
                    print(f"  DIFF {fname} {c}: max {d} (posible revision del Banco)")
                    bad += 1
        print("CHECK OK: coincide con lo committeado" if not bad
              else f"{bad} series con diferencias (revisar si son revisiones del Banco)")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
