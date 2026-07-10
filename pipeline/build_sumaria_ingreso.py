"""Produce la familia de ingreso real (7 tablas): Ginis, percentiles, GIC e
ingreso real nacional/provincial/distrital.

PORTADO SIN REFACTORIZAR de dataset_income.py (ipcr_0 con el metodo oficial
INEI: componentes de ingreso sobre 12*mieperho*ld*i00, deflactor espacial de
17 dominios + temporal por dpto-anio base 2025), dataset_gini.py (Gini
ponderado por curva de Lorenz) y dataset_distribucion.py (percentiles
ponderados + curvas de incidencia del crecimiento).

INSUMOS: ENAHO_RAW (sumaria canonica por anio) + ENAHO_METH (deflactores del
do-file oficial INEI: deflactores_base2025_new.dta y despacial_ldnew.dta,
distribuidos con la metodologia de pobreza 2025).

Out: gini_nacional_tiempo, gini_departamento_tiempo, income_percentiles_tiempo,
     gic_periodos, income_real_national, income_real_province_2021_2025,
     income_real_district_2021_2025

Run:
  ENAHO_RAW=... ENAHO_METH=... python pipeline/build_sumaria_ingreso.py [--check-against data/datasets]
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

INCOME_COMPONENTS = [
    "ingbruhd", "ingindhd",
    "insedthd", "ingseihd", "insedthd1",
    "pagesphd", "paesechd", "ingauthd", "isecauhd", "paesechd1",
    "ingexthd",
    "ingtrahd", "ingtexhd",
    "ingrenhd",
    "ingoexhd", "gru13hd3", "gru23hd3", "gru33hd3", "gru43hd3", "gru53hd3",
    "gru63hd3", "gru73hd3", "gru83hd3", "gru24hd", "gru44hd", "gru54hd",
    "gru74hd", "gru84hd", "gru14hd5",
    "ia01hd", "gru34hd", "gru64hd",
    "gru13hd1", "sig24", "gru23hd1", "gru33hd1", "gru43hd1", "gru53hd1",
    "gru63hd1", "gru73hd1", "gru83hd1", "gru14hd3", "sig26", "sig28",
    "gru13hd2", "ig06hd", "gru23hd2", "gru33hd2", "gru43hd2", "gru53hd2",
    "gru63hd2", "ig08hd", "gru73hd2", "gru83hd2", "gru14hd4",
    "sg42d", "sg42d1", "sg42d2", "sg42d3",
]
NEGATIVE = ["ga04hd"]
PCTS = list(range(5, 100, 5))
WINDOWS = [(2004, 2025), (2004, 2013), (2013, 2019), (2019, 2025)]


def _read_dta_robust(path):
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(path), encoding="latin1")
    except Exception:
        df = pd.read_stata(path, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def real_income(raw: Path, meth: Path, year: int) -> pd.DataFrame:
    df = _read_dta_robust(raw / "sumaria" / f"enaho-{year}-34.dta")
    df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)
    df["dpto"] = df["ubigeo"].str[:2].astype(int)
    df.loc[df["dpto"] == 7, "dpto"] = 15
    est = pd.to_numeric(df["estrato"], errors="coerce")
    dom = pd.to_numeric(df["dominio"], errors="coerce")
    est = est.where(dom != 8, 1)
    df["area"] = np.where(est < 6, 1, 2)

    a = df["area"]
    dA = pd.Series(np.nan, index=df.index)
    for d in range(1, 7):
        dA = dA.where(~((dom == d) & (a == 1)), 2 * d - 1)
        dA = dA.where(~((dom == d) & (a == 2)), 2 * d)
    dA = dA.where(~((dom == 7) & (a == 1)), 13)
    dA = dA.where(~((dom == 7) & (a == 2)), 14)
    sel = (dom == 7) & df["dpto"].isin([16, 17, 25])
    dA = dA.where(~(sel & (a == 1)), 15)
    dA = dA.where(~(sel & (a == 2)), 16)
    dA = dA.where(dom != 8, 17)
    df["dominioa"] = dA

    defl = pd.read_stata(meth / "deflactores_base2025_new.dta", convert_categoricals=False)
    defl.columns = [c.lower() for c in defl.columns]
    defl = defl[defl["aniorec"] == year][["dpto", "i00"]]
    desp = pd.read_stata(meth / "despacial_ldnew.dta", convert_categoricals=False)
    desp.columns = [c.lower() for c in desp.columns]
    df = df.merge(defl, on="dpto", how="left").merge(desp, on="dominioa", how="left",
                                                     suffixes=("", "_sp"))
    df["ld"] = df["ld_sp"] if "ld_sp" in df else df["ld"]

    present = [c for c in INCOME_COMPONENTS if c in df.columns]
    num = df[present].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    for c in NEGATIVE:
        if c in df.columns:
            num = num - pd.to_numeric(df[c], errors="coerce").fillna(0)

    denom = 12 * df["mieperho"] * df["ld"] * df["i00"]
    df["ipcr_0"] = num / denom
    df["factornd07"] = (df["factor07"] * df["mieperho"]).round()
    df["persons"] = df["factor07"] * df["mieperho"]
    df["year"] = year
    return df.dropna(subset=["ipcr_0", "factornd07"])


def wmean(d, val="ipcr_0", w="factornd07"):
    m = d[val].notna() & d[w].notna()
    return float(np.average(d.loc[m, val], weights=d.loc[m, w]))


def wgini(x, w):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = np.clip(x[m], 0, None), w[m]
    if x.size < 2 or w.sum() <= 0:
        return np.nan
    o = np.argsort(x, kind="mergesort")
    x, w = x[o], w[o]
    xw = x * w
    if xw.sum() <= 0:
        return np.nan
    P = np.concatenate([[0], np.cumsum(w) / w.sum()])
    L = np.concatenate([[0], np.cumsum(xw) / xw.sum()])
    area = np.sum((P[1:] - P[:-1]) * (L[1:] + L[:-1]) / 2)
    return round(float(1 - 2 * area), 4)


def wpct(x, w, q):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[m], w[m]
    o = np.argsort(x, kind="mergesort")
    x, w = x[o], w[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return float(np.interp(q, cw, x))


def p90p10(x, w):
    p10 = wpct(x, w, 0.10)
    p90 = wpct(x, w, 0.90)
    return round(p90 / p10, 2) if p10 and p10 > 0 else np.nan


def wquantile(values, weights, qs):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w) - 0.5 * w
    cw /= np.sum(w)
    return np.interp(np.asarray(qs) / 100.0, cw, v)


def aggregate(df, key):
    g = df.groupby(key).apply(
        lambda d: pd.Series({
            "real_pc_income": wmean(d),
            "persons": d["persons"].sum(),
            "n_hh": len(d),
        }), include_groups=False).reset_index()
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("ENAHO_RAW", "peru_raw/enaho"))
    meth = Path(os.environ.get("ENAHO_METH", str(raw / "_methodology_2025")))
    if not (meth / "deflactores_base2025_new.dta").exists():
        print(f"FAIL: deflactores no encontrados en {meth}")
        sys.exit(1)
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS

    per_year = {}
    nat_rows, dep_rows, pct_rows = [], [], []
    for y in range(2004, 2026):
        df = real_income(raw, meth, y)
        per_year[y] = df[["ipcr_0", "persons", "area", "ubigeo"]].assign(
            factornd07=df["factornd07"])
        x, w = df["ipcr_0"].values, df["factornd07"].values
        nat_rows.append({"anio": y, "gini": wgini(x, w),
                         "gini_urbano": wgini(df[df.area == 1]["ipcr_0"], df[df.area == 1]["factornd07"]),
                         "gini_rural": wgini(df[df.area == 2]["ipcr_0"], df[df.area == 2]["factornd07"]),
                         "p90_p10": p90p10(x, w)})
        for dp, sub in df.groupby("dpto"):
            dep_rows.append({"anio": y, "dep": int(dp),
                             "gini": wgini(sub["ipcr_0"], sub["factornd07"])})
        v = df["ipcr_0"].to_numpy(float)
        pw = df["persons"].to_numpy(float)
        qs = wquantile(v, pw, [10, 25, 50, 75, 90])
        pct_rows.append({"year": y, "p10": round(qs[0], 1), "p25": round(qs[1], 1),
                         "mediana": round(qs[2], 1), "p75": round(qs[3], 1),
                         "p90": round(qs[4], 1), "promedio": round(float(np.average(v, weights=pw)), 1),
                         "ratio_p90_p10": round(qs[4] / qs[0], 2)})
        print(f"  {y}: gini={nat_rows[-1]['gini']} mediana={pct_rows[-1]['mediana']}")

    pd.DataFrame(nat_rows).to_csv(outdir / "gini_nacional_tiempo.csv", index=False)
    pd.DataFrame(dep_rows).to_csv(outdir / "gini_departamento_tiempo.csv", index=False)
    pd.DataFrame(pct_rows).to_csv(outdir / "income_percentiles_tiempo.csv", index=False)

    gic_rows = []
    for pctl in PCTS:
        row = {"percentil": pctl}
        for y0, y1 in WINDOWS:
            q0 = wquantile(per_year[y0]["ipcr_0"].to_numpy(float),
                           per_year[y0]["persons"].to_numpy(float), [pctl])[0]
            q1 = wquantile(per_year[y1]["ipcr_0"].to_numpy(float),
                           per_year[y1]["persons"].to_numpy(float), [pctl])[0]
            row[f"crec_{y0}_{y1}"] = round(100 * ((q1 / q0) ** (1 / (y1 - y0)) - 1), 2)
        gic_rows.append(row)
    pd.DataFrame(gic_rows).to_csv(outdir / "gic_periodos.csv", index=False)

    # nacional + provincia/distrito 2021 vs 2025 (dataset_income verbatim)
    yA, yB = 2021, 2025
    dfs = {y: real_income(raw, meth, y) for y in (yA, yB)}
    val_rows = []
    for y in (yA, yB):
        d = dfs[y]
        val_rows.append({"year": y, "real_pc_income_national": round(wmean(d), 1),
                         "urban": round(wmean(d[d.area == 1]), 1),
                         "rural": round(wmean(d[d.area == 2]), 1),
                         "population": round(d["persons"].sum())})
    pd.DataFrame(val_rows).to_csv(outdir / "income_real_national.csv", index=False)
    for key, name in [("ubigeo", "district"), ("prov", "province")]:
        for y in (yA, yB):
            dfs[y]["prov"] = dfs[y]["ubigeo"].str[:4]
        gA = aggregate(dfs[yA], key).rename(columns={"real_pc_income": f"income_{yA}",
                                                     "persons": f"pop_{yA}", "n_hh": f"nhh_{yA}"})
        gB = aggregate(dfs[yB], key).rename(columns={"real_pc_income": f"income_{yB}",
                                                     "persons": f"pop_{yB}", "n_hh": f"nhh_{yB}"})
        m = gA.merge(gB, on=key, how="outer")
        m["chg_pct"] = 100 * (m[f"income_{yB}"] / m[f"income_{yA}"] - 1)
        m["chg_soles"] = m[f"income_{yB}"] - m[f"income_{yA}"]
        m.sort_values("chg_pct").to_csv(outdir / f"income_real_{name}_{yA}_{yB}.csv", index=False)

    if a.check_against:
        refdir = Path(a.check_against)
        names = ["gini_nacional_tiempo.csv", "gini_departamento_tiempo.csv",
                 "income_percentiles_tiempo.csv", "gic_periodos.csv",
                 "income_real_national.csv", "income_real_province_2021_2025.csv",
                 "income_real_district_2021_2025.csv"]
        bad = 0
        for n in names:
            ref = pd.read_csv(refdir / n)
            new = pd.read_csv(outdir / n)
            if list(ref.columns) != list(new.columns) or len(ref) != len(new):
                print(f"  FAIL forma {n}: ref {ref.shape} vs new {new.shape}")
                bad += 1
                continue
            ok = True
            for c in ref.columns:
                rv = pd.to_numeric(ref[c], errors="coerce")
                nv = pd.to_numeric(new[c], errors="coerce")
                if rv.notna().any():
                    d = (rv - nv).abs().max()
                    if pd.notna(d) and d > 1e-3:
                        print(f"  FAIL {n} col {c}: max diff {d}")
                        ok = False
                        break
                elif not ref[c].astype(str).equals(new[c].astype(str)):
                    print(f"  FAIL {n} col {c}: texto")
                    ok = False
                    break
            bad += 0 if ok else 1
        print(f"comparadas {len(names)} tablas, {bad} con diferencias")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
