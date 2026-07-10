"""Produce las 10 matrices de movilidad de ingresos del panel (quintil a quintil).

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/panel_movilidad_ingreso.py:
quintiles ponderados POR OLA (w_panel) del ingreso per capita nominal
(inghog2d/mieperho), primera ola vs ultima del panel balanceado, matriz 5x5
normalizada por fila.

INSUMO DECLARADO: el parquet largo enaho_panel_hogar_long.parquet (1.6M filas,
construido por build_panel_dataset.py — su porteo es W2c, el archivo vive en
el workspace y su productor esta publicado en pipeline-archive).

Run:
  PANEL_LONG=ruta/al/parquet python pipeline/build_panel_movilidad.py [--check-against data/datasets]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"


def _wquintile(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    out = np.zeros(len(x), int)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if ok.sum() < 5:
        return out
    xi, wi, idx = x[ok], w[ok], np.where(ok)[0]
    order = np.argsort(xi, kind="mergesort")
    cw = np.cumsum(wi[order]) / wi.sum()
    q = np.searchsorted([0.2, 0.4, 0.6, 0.8], cw, side="right") + 1
    out[idx[order]] = q
    return out


def matrix_for(label: str, df: pd.DataFrame):
    sub = df[(df["window"].astype(str) == df["window"].astype(str)) & (df["in_balanced"] == 1)].copy()
    y0, y1 = (2000 + int(label[:2]) if False else int(label.split("-")[0]),
              int(label.split("-")[1]) if len(label.split("-")[1]) == 4
              else 2000 + int(label.split("-")[1]))
    sub = sub[(sub["anio"] >= y0) & (sub["anio"] <= y1)]
    sub = sub[sub["release"] == sub["release"].mode().iloc[0]] if len(sub) else sub
    if sub.empty:
        return None
    sub["ypc"] = sub["inghog2d"] / sub["mieperho"].replace(0, np.nan)
    waves = sorted(sub["anio"].unique())
    first, last = waves[0], waves[-1]
    qcols = {}
    for wv in (first, last):
        d = sub[sub["anio"] == wv]
        q = _wquintile(d["ypc"].values, d["w_panel"].fillna(0).values)
        qcols[wv] = pd.Series(q, index=d["hhid"].values)
    a = qcols[first].rename("q0").to_frame().join(qcols[last].rename("q1"), how="inner")
    wlast = sub[sub["anio"] == last].set_index("hhid")["w_panel"]
    a = a.join(wlast.rename("w"), how="left")
    a = a[(a["q0"] >= 1) & (a["q1"] >= 1) & a["w"].notna()]
    M = np.zeros((5, 5))
    for i in range(1, 6):
        for j in range(1, 6):
            M[i - 1, j - 1] = a.loc[(a["q0"] == i) & (a["q1"] == j), "w"].sum()
    row = M.sum(axis=1, keepdims=True)
    P = np.divide(M, row, out=np.zeros_like(M), where=row > 0) * 100
    return P, first, last, int(len(a))


def run(label: str, df: pd.DataFrame, outdir: Path):
    res = matrix_for(label, df)
    if res is None:
        print(f"[skip] {label}: sin datos")
        return
    P, first, last, n = res
    pd.DataFrame(P, index=[f"q{i}_origen" for i in range(1, 6)],
                 columns=[f"q{j}_destino" for j in range(1, 6)]).round(1).to_csv(
        outdir / f"panel_movilidad_quintil_{label}.csv")
    print(f"[{label}] n={n:,} permanece={np.diag(P).mean():.0f}% Q1->Q1={P[0,0]:.0f}%")


def compare(newdir: Path, refdir: Path) -> int:
    bad = 0
    files = sorted(newdir.glob("panel_movilidad_quintil_*.csv"))
    for p in files:
        ref = refdir / p.name
        if not ref.exists():
            print(f"  NUEVO sin referencia: {p.name}")
            continue
        a = pd.read_csv(ref)
        b = pd.read_csv(p)
        same = list(a.columns) == list(b.columns) and len(a) == len(b)
        if same:
            for c in a.columns[1:]:
                d = (pd.to_numeric(a[c], errors="coerce") - pd.to_numeric(b[c], errors="coerce")).abs().max()
                if pd.notna(d) and d > 1e-3:
                    same = False
                    print(f"  FAIL {p.name} col {c}: {d}")
                    break
        else:
            print(f"  FAIL forma {p.name}")
        bad += 0 if same else 1
    print(f"comparadas {len(files)} matrices, {bad} con diferencias")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    parquet = Path(os.environ.get("PANEL_LONG", "enaho_panel_hogar_long.parquet"))
    if not parquet.exists():
        print(f"FAIL: PANEL_LONG no existe: {parquet}")
        sys.exit(1)
    df = pd.read_parquet(parquet)
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS
    labels = []
    for w in sorted(df["window"].dropna().unique()):
        ws = str(int(w)).zfill(4)
        labels.append(f"20{ws[:2]}-20{ws[2:]}")
    for lab in labels:
        run(lab, df, outdir)
    if a.check_against:
        sys.exit(1 if compare(outdir, Path(a.check_against)) else 0)


if __name__ == "__main__":
    main()
