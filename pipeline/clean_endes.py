"""Produce los insumos limpios ENDES (W5c): endes_mujeres_2004_2024 y
endes_nacimientos_2004_2024.

PORTADO SIN REFACTORIZAR de clean_endes_women.py y clean_endes_nacimientos.py:
deteccion de recodes POR CONTENIDO (los nombres de archivo cambian cada año),
merges por caseid anclados en el IR core, universo MEF 15-49 (la extension
12-14 de 2018+ queda fuera del panel comparable), peso v005/1e6, y cada
registro asignado a su año calendario verdadero (_endes_units, archivos
acumulativos 2004-2008).

Nota: estos CSV son MICRODATA (63MB + 136MB) — insumos de build_endes.py,
excluidos de la app y de git. El modo --check-against verifica contra los
committeados del workspace.

Run:
  ENDES_RAW=... python pipeline/clean_endes.py [--check-against D:/ENAHO_ANALYSIS/datasets]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _endes_units as eu  # noqa: E402

WANT = {
    "wt_raw": "v005", "edad": "v012", "grupo_edad": "v013", "educ_nivel": "v106",
    "educ_anios": "v133", "educ_logro": "v149", "region_dhs": "v024", "area": "v025",
    "riqueza": "v190", "cluster": "v001",
    "hijos_nacidos": "v201", "embarazada": "v213", "edad_primer_hijo": "v212", "nac_ult5": "v208",
    "estado_civil": "v501", "edad_primera_union": "v511", "cmc_ent": "v008",
    "depto": "sdepart", "region_inei": "sregion", "provincia": "sprovin",
    "distrito": "sdistri", "sweight": "sweight",
}
SRC2DEST = {v: k for k, v in WANT.items()}
BIRTH = {"orden": "bord", "multiple": "b0", "mes_nac": "b1", "anio_nac": "b2",
         "cmc_nac": "b3", "sexo": "b4", "vivo": "b5", "edad_muerte_meses": "b7",
         "edad_actual": "b8", "intervalo_meses": "b11"}
MOTHER = {"wt_raw": "v005", "madre_edad": "v012", "madre_educ": "v106",
          "madre_cmc_nac": "v011", "cmc_entrevista": "v008", "region": "v024", "area": "v025"}


def women_year(year: int) -> pd.DataFrame | None:
    code = eu.ENDES_CODE[year]
    d = eu.dir_for(year)
    if not d.exists():
        print(f"  {year}: not downloaded -> skip")
        return None
    metas = {}
    for p in sorted(d.rglob("*.sav")):
        try:
            _, m = pyreadstat.read_sav(str(p), metadataonly=True)
        except Exception:
            continue
        cl = {c.lower(): c for c in m.column_names}
        if "caseid" in cl:
            metas[p] = (cl, m.number_rows)
    cores = [p for p, (cl, _) in metas.items() if "v012" in cl and "v106" in cl]
    if not cores:
        cores = [p for p, (cl, _) in metas.items() if "v012" in cl]
    if not cores:
        print(f"  {year}: no IR core recode -> skip")
        return None
    core = max(cores, key=lambda p: metas[p][1])
    order = [core] + [p for p in metas if p != core]
    result = None
    pulled: set[str] = set()
    for p in order:
        cl, _ = metas[p]
        here = [s for s in SRC2DEST if s in cl and s not in pulled]
        if not here:
            continue
        use = [cl["caseid"]] + [cl[s] for s in here]
        df, _ = pyreadstat.read_sav(str(p), usecols=use)
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={s: SRC2DEST[s] for s in here})
        df["caseid"] = df["caseid"].astype(str).str.strip()
        df = df.drop_duplicates("caseid")[["caseid"] + [SRC2DEST[s] for s in here]]
        result = df if result is None else result.merge(df, on="caseid", how="left")
        pulled.update(here)
    if result is None:
        return None
    if "cmc_ent" in result.columns:
        result = result[eu.true_year_mask(result, year, "cmc_ent")].copy()
    edad = pd.to_numeric(result["edad"], errors="coerce")
    result = result[edad.between(15, 49)].copy()
    result["wt"] = pd.to_numeric(result.get("wt_raw"), errors="coerce") / 1e6
    result["anio"] = year
    result["codigo"] = code
    return result


def _cols(p: Path) -> dict:
    _, m = pyreadstat.read_sav(str(p), metadataonly=True)
    return {c.lower(): c for c in m.column_names}


def _read(p: Path, cl: dict, want: dict, key: list[str]) -> pd.DataFrame:
    src = [k for k in key if k in cl] + [v for v in want.values() if v in cl]
    df, _ = pyreadstat.read_sav(str(p), usecols=[cl[s] for s in src])
    df.columns = [c.lower() for c in df.columns]
    return df.rename(columns={v: k for k, v in want.items() if v in df.columns})


def nac_year(year: int) -> pd.DataFrame | None:
    code = eu.ENDES_CODE[year]
    d = eu.dir_for(year)
    if not d.exists():
        return None
    cols = {p: _cols(p) for p in sorted(d.rglob("*.sav"))}
    br = next((p for p, cl in cols.items() if "caseid" in cl and "bidx" in cl and "b3" in cl), None)
    if br is None:
        print(f"  {year}: no birth recode -> skip")
        return None
    df = _read(br, cols[br], BIRTH, ["caseid", "bidx"])
    df["caseid"] = df["caseid"].astype(str).str.strip()
    ir = next((p for p, cl in cols.items() if "caseid" in cl and "v012" in cl and "v106" in cl), None)
    if ir:
        mo = _read(ir, cols[ir], MOTHER, ["caseid"])
        mo["caseid"] = mo["caseid"].astype(str).str.strip()
        df = df.merge(mo.drop_duplicates("caseid"), on="caseid", how="left")
    if "cmc_nac" in df and "madre_cmc_nac" in df:
        df["madre_edad_al_nacer"] = (pd.to_numeric(df["cmc_nac"], errors="coerce")
                                     - pd.to_numeric(df["madre_cmc_nac"], errors="coerce")) / 12.0
    df["wt"] = pd.to_numeric(df.get("wt_raw"), errors="coerce") / 1e6
    if "cmc_entrevista" in df.columns:
        df = df[eu.true_year_mask(df, year, "cmc_entrevista")].copy()
    df["anio_encuesta"] = year
    df["codigo"] = code
    return df


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    wf, bf = [], []
    for y in eu.years(2004, 2024):
        print(f"== {y} ==")
        w = women_year(y)
        if w is not None:
            wf.append(w)
            print(f"  mujeres n={len(w)}")
        b = nac_year(y)
        if b is not None:
            bf.append(b)
            print(f"  nacimientos n={len(b)}")
    allw = pd.concat(wf, ignore_index=True)
    front = ["anio", "codigo", "caseid", "wt", "edad", "grupo_edad", "educ_nivel",
             "educ_anios", "area", "depto", "region_dhs", "riqueza", "estado_civil",
             "hijos_nacidos", "embarazada", "edad_primer_hijo", "edad_primera_union", "nac_ult5"]
    allw = allw[[c for c in front if c in allw.columns] + [c for c in allw.columns if c not in front]]
    allb = pd.concat(bf, ignore_index=True)
    frontb = ["anio_encuesta", "codigo", "caseid", "bidx", "wt", "orden", "sexo",
              "mes_nac", "anio_nac", "cmc_nac", "vivo", "edad_actual", "edad_muerte_meses",
              "intervalo_meses", "madre_edad", "madre_edad_al_nacer", "madre_educ", "region", "area"]
    allb = allb[[c for c in frontb if c in allb.columns] + [c for c in allb.columns if c not in frontb]]
    return allw, allb


def cmp_df(ref: pd.DataFrame, new: pd.DataFrame, key: list[str], name: str) -> int:
    if len(ref) != len(new) or list(ref.columns) != list(new.columns):
        print(f"FAIL forma {name}: ref {ref.shape} vs new {new.shape}")
        print(f"  ref cols: {list(ref.columns)}")
        print(f"  new cols: {list(new.columns)}")
        return 1
    r = ref.sort_values(key).reset_index(drop=True)
    n = new.sort_values(key).reset_index(drop=True)
    for c in ref.columns:
        rv = pd.to_numeric(r[c], errors="coerce")
        nv = pd.to_numeric(n[c], errors="coerce")
        if rv.notna().any():
            d = (rv - nv).abs().max()
            if pd.notna(d) and d > 1e-3:
                print(f"FAIL {name} col {c}: max diff {d}")
                return 1
        elif not r[c].astype(str).equals(n[c].astype(str)):
            print(f"FAIL {name} col {c}: texto difiere")
            return 1
    print(f"CHECK OK {name}: {len(ref):,} filas x {len(ref.columns)} columnas")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    allw, allb = build()
    if a.check_against:
        refdir = Path(a.check_against)
        bad = cmp_df(pd.read_csv(refdir / "endes_mujeres_2004_2024.csv"), allw,
                     ["anio", "caseid"], "mujeres")
        bad += cmp_df(pd.read_csv(refdir / "endes_nacimientos_2004_2024.csv"), allb,
                      ["anio_encuesta", "caseid", "bidx"], "nacimientos")
        sys.exit(1 if bad else 0)
    out = Path(tempfile.gettempdir())
    allw.to_csv(out / "endes_mujeres_2004_2024.csv", index=False)
    allb.to_csv(out / "endes_nacimientos_2004_2024.csv", index=False)
    print(f"wrote microdata inputs to {out} (no van a git)")


if __name__ == "__main__":
    main()
