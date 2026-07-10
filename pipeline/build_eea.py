"""Produce la productividad EEA (VA por trabajador): sector, tamano y pivote.

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/build_eea_productividad.py
(cruce IRUC de Clave 88 del Estado de Produccion con Clave 08 de personal,
ratio de totales ponderados, solo F2 grandes). Unico cambio de plomeria: el
glob relativo "raw/eea_inei" del original se parametriza en EEA_RAW.

Las otras 8 tablas EEA siguen en pipeline-archive (W5c).

Crudos: EEA_RAW (dirs <csv_code>/ de perudata.eea + _eea_manifest.csv).

Run:
  EEA_RAW=... python pipeline/build_eea.py
  EEA_RAW=... python pipeline/build_eea.py --check-against data/datasets
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
MOD2SEC = {
    "Comercio": "Comercio", "Manufactura": "Manufactura", "Construc": "Construccion",
    "Transportes": "Transp./Comunic.", "Servicios Electricos": "Electr./Agua",
    "Pesca": "Agro/Pesca", "Acuicult": "Agro/Pesca", "Hospedaje": "Aloj./Restaurantes",
    "Restaurantes": "Aloj./Restaurantes", "Agencia de Viajes": "Otros servicios",
    "Centros Educativos": "Otros servicios", "Universidades": "Otros servicios",
    "Servicios": "Otros servicios",
}
BINS = [0, 50, 200, 500, np.inf]
BINLAB = ["1-50", "51-200", "201-500", "500+"]
TABLES = ["eea_productividad_sector.csv", "eea_productividad_tamano.csv",
          "eea_productividad_sector_tamano.csv"]


def sec_of(n):
    for k, v in MOD2SEC.items():
        if k.lower() in n.lower():
            return v


def rd(f):
    sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
    d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    return d.rename(columns={d.columns[0]: 'iruc'})


def build(raw: Path, outdir: Path) -> None:
    m = pd.read_csv(raw / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    firms = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        files = glob.glob(str(raw / str(r.csv_code) / "**" / "*.csv"), recursive=True)
        c03 = [x for x in files if re.search(r'_c03_1\.csv$', x)]
        c10 = [x for x in files if re.search(r'_c10_1\.csv$', x)]
        if not c03 or not c10:
            continue
        va = rd(c03[0])
        if 'clave' not in va.columns:
            continue
        cl = pd.to_numeric(va['clave'], errors='coerce')
        va = va[cl == 88][['iruc', 'dato1', 'factor_exp']].rename(columns={'dato1': 'va'})
        va['va'] = pd.to_numeric(va['va'], errors='coerce')
        em = rd(c10[0])
        ce = pd.to_numeric(em['clave'], errors='coerce')
        em = em[ce == 8][['iruc', 'dato1']].rename(columns={'dato1': 'trab'})
        em['trab'] = pd.to_numeric(em['trab'], errors='coerce')
        g = va.merge(em, on='iruc', how='inner')
        g['w'] = pd.to_numeric(g['factor_exp'], errors='coerce')
        g['sector'] = sec
        firms.append(g[['sector', 'va', 'trab', 'w']])
    f = pd.concat(firms).dropna(subset=['va', 'trab', 'w'])
    f = f[f.trab > 0]
    bs = f.groupby('sector').apply(lambda x: pd.Series({
        "trab": (x.w * x.trab).sum(), "va": (x.w * x.va).sum(),
        "va_x_trab": (x.w * x.va).sum() / (x.w * x.trab).sum()}), include_groups=False).reset_index()
    bs = bs.sort_values("va_x_trab", ascending=False)
    bs.to_csv(outdir / "eea_productividad_sector.csv", index=False, encoding="utf-8")
    f['tam'] = pd.cut(f.trab, bins=BINS, labels=BINLAB)
    bt = f.groupby('tam', observed=True).apply(lambda x: pd.Series({
        "n": len(x), "trab": (x.w * x.trab).sum(), "va": (x.w * x.va).sum(),
        "va_x_trab": (x.w * x.va).sum() / (x.w * x.trab).sum()}), include_groups=False).reset_index()
    bt.to_csv(outdir / "eea_productividad_tamano.csv", index=False, encoding="utf-8")
    piv = (f.groupby(['sector', 'tam'], observed=True)
           .apply(lambda x: (x.w * x.va).sum() / (x.w * x.trab).sum(), include_groups=False)
           .unstack() / 1000).round(1)
    piv.to_csv(outdir / "eea_productividad_sector_tamano.csv", encoding="utf-8")
    print(f"sectores {len(bs)}, clases de tamano {len(bt)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("EEA_RAW", "peru_raw/eea"))
    if not raw.exists():
        print(f"FAIL: EEA_RAW no existe: {raw}")
        sys.exit(1)
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS
    build(raw, outdir)
    if a.check_against:
        ref_dir = Path(a.check_against)
        bad = 0
        for n in TABLES:
            ref = pd.read_csv(ref_dir / n)
            new = pd.read_csv(outdir / n)
            if list(ref.columns) != list(new.columns) or len(ref) != len(new):
                print(f"  FAIL forma {n}: ref {ref.shape} vs new {new.shape}")
                bad += 1
                continue
            for c in ref.columns:
                rv = pd.to_numeric(ref[c], errors="coerce")
                nv = pd.to_numeric(new[c], errors="coerce")
                if rv.notna().any():
                    d = (rv - nv).abs().max()
                    if pd.notna(d) and d > 1e-3:
                        print(f"  FAIL {n} col {c}: max diff {d}")
                        bad += 1
                        break
                elif not ref[c].astype(str).equals(new[c].astype(str)):
                    print(f"  FAIL {n} col {c}: texto difiere")
                    bad += 1
                    break
        print(f"comparadas {len(TABLES)} tablas, {bad} con diferencias")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
