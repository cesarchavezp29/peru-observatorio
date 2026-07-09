"""Produce official_poverty_replication.csv desde microdatos crudos via perudata.

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/reproduce_official.py, cuya
logica vive hoy en perudata.validate (misma construccion: persona = factor07 x
mieperho, pobre = pobreza in {1,2}, sumaria canonica, lector v110-proof).

Este script ES el gate de validacion: si algun año se desvia de la cifra INEI
publicada, sale con codigo 1 y el CI rompe. "Lo que no valida, no se publica",
ejecutable.

Datos crudos: perudata los descarga a PERUDATA_DIR (o ./peru_raw). En CI la
cache de Actions conserva los vintages historicos (nunca cambian).

Run:  python pipeline/build_sumaria.py [--check-against data/datasets/...csv]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from perudata import validate

OUT = Path(__file__).resolve().parent.parent / "data" / "datasets" / "official_poverty_replication.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None,
                    help="CSV committeado: verifica valor por valor y NO escribe")
    a = ap.parse_args()

    df = validate.poverty(verbose=False)
    if df.empty:
        print("FAIL: sin datos (descarga de sumaria fallo)")
        sys.exit(1)

    # gate: cualquier desviacion de la cifra oficial rompe el build
    matched = df.dropna(subset=["official_poverty"])
    bad = matched[matched["pov_diff"].abs() > 0.05]
    if len(bad):
        print("GATE FAIL: la replica se desvia de INEI en:")
        print(bad[["year", "poverty_pct", "official_poverty", "pov_diff"]].to_string(index=False))
        sys.exit(1)
    print(f"GATE OK: pobreza oficial replicada exacta en {len(matched)}/{len(matched)} años")

    if a.check_against:
        ref = pd.read_csv(a.check_against)
        if list(ref.columns) != list(df.columns):
            print(f"FAIL: columnas difieren\n  ref: {list(ref.columns)}\n  new: {list(df.columns)}")
            sys.exit(1)
        merged = ref.merge(df, on="year", suffixes=("_ref", "_new"))
        diffs = []
        for c in ref.columns:
            if c == "year":
                continue
            d = (pd.to_numeric(merged[f"{c}_ref"], errors="coerce")
                 - pd.to_numeric(merged[f"{c}_new"], errors="coerce")).abs().max()
            if pd.notna(d) and d > 1e-6:
                diffs.append((c, d))
        if diffs:
            print(f"FAIL: valores difieren del CSV committeado: {diffs}")
            sys.exit(1)
        print(f"CHECK OK: {len(ref)} filas x {len(ref.columns)} columnas coinciden valor por valor")
        return

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(df)} filas)")


if __name__ == "__main__":
    main()
