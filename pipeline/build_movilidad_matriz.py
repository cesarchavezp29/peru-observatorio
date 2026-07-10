"""Produce la matriz de movilidad educativa intergeneracional (jefe -> hijos).

METODO (descriptivo, limitacion declarada): hijos e hijas ADULTOS (22-30,
p203==3) que corresiden con el jefe del hogar, en ENAHO M02 (parentesco) x M03
(educacion). Nivel en 3 grupos verificados (p301a: <=4 primaria o menos, 5-6
secundaria, 7-11 superior, 12 excluido). Ponderado por factor07. Dos epocas
agrupadas para muestra: 2004-2011 y 2018-2025.

LIMITE ESTRUCTURAL (impreso en la tabla y en la pagina): los adultos jovenes
que AUN viven con sus padres no son una muestra aleatoria — los que ya se
fueron de casa no aparecen. La matriz describe la transmision entre
corresidentes, el estandar que ENAHO permite sin registro de padres.

Out: data/datasets/movilidad_matriz_educacion.csv (largo: epoca, origen, destino, pct, n)
     + una tabla ancha por epoca para el heatmap del Explorer.

Run:  ENAHO_RAW=... python pipeline/build_movilidad_matriz.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
HK = ["conglome", "vivienda", "hogar"]
EPOCAS = {"2004-2011": range(2004, 2012), "2018-2025": range(2018, 2026)}
NIVEL = {"primaria": (1, 4), "secundaria": (5, 6), "superior": (7, 11)}


def rd(raw, folder, mod, year, cols):
    fp = raw / folder / f"enaho-{year}-{mod}.dta"
    if not fp.exists():
        return None
    have = pyreadstat.read_dta(str(fp), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    use = [cl[c] for c in cols if c in cl]
    d, _ = pyreadstat.read_dta(str(fp), encoding="latin1", usecols=use)
    d.columns = [c.lower() for c in d.columns]
    return d


def num(s):
    return pd.to_numeric(s, errors="coerce")


def hkey(d):
    return d[HK].apply(lambda c: num(c).astype("Int64").astype(str)).agg("-".join, axis=1)


def grupo(p301a):
    g = pd.Series(pd.NA, index=p301a.index, dtype="object")
    for name, (lo, hi) in NIVEL.items():
        g[p301a.between(lo, hi)] = name
    return g


def build(raw: Path) -> pd.DataFrame:
    rows = []
    for epoca, years in EPOCAS.items():
        pairs = []
        for y in years:
            m2 = rd(raw, "miembros", "02", y, HK + ["codperso", "p203"])
            m3 = rd(raw, "educacion", "03", y, HK + ["codperso", "p301a", "p208a", "factor07"])
            if m2 is None or m3 is None:
                continue
            m2["hh"] = hkey(m2)
            m3["hh"] = hkey(m3)
            m2["codperso"] = num(m2["codperso"])
            m3["codperso"] = num(m3["codperso"])
            # jefe del hogar y su educacion
            jefes = m2[num(m2["p203"]) == 1][["hh", "codperso"]]
            edu = m3[["hh", "codperso", "p301a", "p208a", "factor07"]].copy()
            edu["p301a"] = num(edu["p301a"])
            je = jefes.merge(edu[["hh", "codperso", "p301a"]], on=["hh", "codperso"], how="left")
            je = je.rename(columns={"p301a": "edu_jefe"})[["hh", "edu_jefe"]].dropna()
            # hijos adultos corresidentes (22-30)
            hijos = m2[num(m2["p203"]) == 3][["hh", "codperso"]]
            hi = hijos.merge(edu, on=["hh", "codperso"], how="left")
            hi["edad"] = num(hi["p208a"])
            hi = hi[hi["edad"].between(22, 30)]
            d = hi.merge(je, on="hh", how="inner")
            d["origen"] = grupo(num(d["edu_jefe"]))
            d["destino"] = grupo(num(d["p301a"]))
            d = d.dropna(subset=["origen", "destino", "factor07"])
            pairs.append(d[["origen", "destino", "factor07"]])
        if not pairs:
            continue
        p = pd.concat(pairs)
        for org in NIVEL:
            sub = p[p["origen"] == org]
            tot = sub["factor07"].sum()
            for dst in NIVEL:
                w = sub.loc[sub["destino"] == dst, "factor07"].sum()
                rows.append({"epoca": epoca, "origen": org, "destino": dst,
                             "pct": round(100 * w / tot, 1) if tot else np.nan,
                             "n": int((sub["destino"] == dst).sum())})
        print(f"[{epoca}] pares jefe-hijo 22-30: {sum(len(x) for x in pairs):,}")
    return pd.DataFrame(rows)


def main() -> None:
    raw = Path(os.environ.get("ENAHO_RAW", "peru_raw/enaho"))
    if not raw.exists():
        print(f"FAIL: ENAHO_RAW no existe: {raw}")
        sys.exit(1)
    df = build(raw)
    if df.empty:
        print("FAIL: sin datos")
        sys.exit(1)
    df.to_csv(DATASETS / "movilidad_matriz_educacion.csv", index=False)
    # ancho por epoca reciente para el heatmap generico del Explorer
    rec = df[df["epoca"] == "2018-2025"].pivot(index="origen", columns="destino", values="pct")
    rec = rec.reindex(index=list(NIVEL), columns=list(NIVEL))
    rec.index = [f"{i}_origen" for i in rec.index]
    rec.columns = [f"{c}_destino" for c in rec.columns]
    rec.reset_index(names="nivel_jefe").to_csv(
        DATASETS / "movilidad_matriz_educacion_2018_2025.csv", index=False)
    print(df.pivot_table(index=["epoca", "origen"], columns="destino", values="pct").to_string())


if __name__ == "__main__":
    main()
