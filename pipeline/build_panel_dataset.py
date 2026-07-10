"""Produce enaho_panel_hogar_long.parquet: EL panel largo de hogares (W2c).

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/build_panel_dataset.py:
una fila por (release, hogar, ola) desde las sumarias WIDE de los 10 releases,
con ambos pesos (w_xsec por ola y w_panel longitudinal, ambos expandidos por
mieperho) y el flag de panel balanceado. Es el insumo de
build_panel_movilidad.py y del resto de dinamicas.

Crudos: PANEL_RAW (dirs <release>_<codigo> con sumaria*.dta, mismo layout que
descarga perudata.panel). Solo sumarias — los modulos de persona no se tocan.

Run:
  PANEL_RAW=... python pipeline/build_panel_dataset.py [--check-against ruta/al/parquet]
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _panel_keys as pk  # noqa: E402

warnings.filterwarnings("ignore")

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
PANEL_CODE = {2011: 302, 2015: 529, 2016: 614, 2017: 612, 2018: 651,
              2019: 699, 2020: 743, 2021: 763, 2022: 845, 2023: 912}
BASES = ["pobreza", "inghog2d", "gashog2d", "linea", "linpe", "mieperho",
         "dominio", "estrato"]


def _sumaria(raw: Path, release: int) -> Path | None:
    d = raw / f"{release}_{PANEL_CODE[release]}"
    if not d.exists():
        return None
    c = [p for p in d.glob("*.dta") if "sumaria" in p.name.lower() and "12g" not in p.name.lower()]
    return c[0] if c else None


def build_release(raw: Path, release: int) -> pd.DataFrame | None:
    path = _sumaria(raw, release)
    if not path:
        return None
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, flag = pk.longest_window(cl)
    if not win:
        return None
    years = pk.window_years(win)

    anchset = pk.anchors(cl)
    want = [cl[a] for a in anchset]
    if flag:
        want.append(cl[flag])
    pw_col = pk.lweight_col(cl, win)
    if pw_col:
        want.append(cl[pw_col])
    for y in years:
        s = f"{y % 100:02d}"
        for b in BASES:
            if f"{b}_{s}" in cl:
                want.append(cl[f"{b}_{s}"])
        xs = pk.xsec_weight_col(cl, s)
        if xs:
            want.append(cl[xs])
    if "factor07" in cl:
        want.append(cl["factor07"])
    want = list(dict.fromkeys(want))
    df, _ = pyreadstat.read_dta(str(path), usecols=want)
    dcl = {c.lower(): c for c in df.columns}

    frames = []
    for y in years:
        s = f"{y % 100:02d}"
        if f"pobreza_{s}" not in dcl:
            continue
        sub = pd.DataFrame()
        for a in anchset:
            if a in dcl:
                sub[a] = df[dcl[a]]
        sub["release"] = release
        sub["window"] = win
        sub["anio"] = y
        for b in BASES:
            sub[b] = df[dcl[f"{b}_{s}"]] if f"{b}_{s}" in dcl else np.nan
        miep = sub["mieperho"].fillna(1)
        xs = pk.xsec_weight_col(dcl, s)
        sub["w_xsec"] = (df[dcl[xs]].fillna(0) * miep) if xs else np.nan
        if flag and flag in dcl:
            inbal = (df[dcl[flag]] == 1)
            sub["in_balanced"] = inbal.astype(int)
            pw = pk.lweight_col(dcl, win)
            sub["w_panel"] = (np.where(inbal, df[dcl[pw]].fillna(0) * miep, np.nan)
                              if pw else np.nan)
        else:
            sub["in_balanced"] = 0
            sub["w_panel"] = np.nan
        frames.append(sub)

    out = pd.concat(frames, ignore_index=True)
    out = out[out["pobreza"].notna()].copy()
    out["poor"] = out["pobreza"].isin([1, 2]).astype(int)
    keycols = [a for a in anchset if a in out.columns]
    out["hhid"] = (out["release"].astype(str) + "_" +
                   out[keycols].astype("Int64").astype(str).agg("-".join, axis=1))
    out = out.rename(columns={"conglome": "cong", "vivienda": "vivi"})
    cols = ["release", "window", "hhid", "cong", "vivi", "num_hog", "anio",
            "pobreza", "poor", "inghog2d", "gashog2d", "linea", "linpe",
            "mieperho", "dominio", "estrato", "w_xsec", "w_panel", "in_balanced"]
    return out[[c for c in cols if c in out.columns]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("PANEL_RAW", "peru_raw/enaho_panel"))
    if not raw.exists():
        print(f"FAIL: PANEL_RAW no existe: {raw}")
        sys.exit(1)
    parts = []
    for rel in sorted(PANEL_CODE):
        d = build_release(raw, rel)
        if d is None:
            print(f"[skip] release {rel}")
            continue
        print(f"[ok] release {rel} window {d['window'].iloc[0]}: {len(d):,} filas")
        parts.append(d)
    panel = pd.concat(parts, ignore_index=True)
    print(f"TOTAL: {len(panel):,} filas hogar-ola")

    if a.check_against:
        ref = pd.read_parquet(a.check_against)
        if len(ref) != len(panel) or list(ref.columns) != list(panel.columns):
            print(f"FAIL forma: ref {ref.shape} {list(ref.columns)[:6]}... vs new {panel.shape}")
            sys.exit(1)
        key = ["release", "hhid", "anio"]
        r = ref.sort_values(key).reset_index(drop=True)
        n = panel.sort_values(key).reset_index(drop=True)
        bad = []
        for c in ref.columns:
            rv = pd.to_numeric(r[c], errors="coerce")
            nv = pd.to_numeric(n[c], errors="coerce")
            if rv.notna().any():
                dmax = (rv - nv).abs().max()
                if pd.notna(dmax) and dmax > 1e-3:
                    bad.append((c, float(dmax)))
            elif not r[c].astype(str).equals(n[c].astype(str)):
                bad.append((c, "texto"))
        if bad:
            print(f"FAIL: difiere del parquet committeado: {bad}")
            sys.exit(1)
        print(f"CHECK OK: {len(ref):,} filas x {len(ref.columns)} columnas coinciden valor por valor")
        return

    out = DATASETS.parent.parent / "data" / "datasets" / "enaho_panel_hogar_long.parquet"
    panel.to_parquet(out, index=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
