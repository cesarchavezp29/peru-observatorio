"""
dataset_income.py  -  REAL per-capita income, INEI official methodology
=======================================================================
Reproduces INEI's "Ingreso real promedio per cápita mensual a precios de Lima"
(variable ipcr_0 in INEI's do-file `01_ConstrVarGastoIngreso2015-2025.do`),
then aggregates it to DISTRICT and PROVINCE for a chosen pair of years.

Why this and not a crude inghog2d/people:
  * INEI deflates income at the COMPONENT level by two deflators:
      - ld  : SPATIAL deflator (cost of living by 17 geographic domains, Lima=1)
      - i00 : TEMPORAL deflator to a base year (base 2025 here), by dpto x year
  * ipcr_0 = Σ(income components) / (12 * mieperho * ld * i00)
  * Result = constant 2025 soles "a precios de Lima" -> 2021 and 2025 are
    directly comparable in real terms.

No module merge is needed: everything lives in canonical Sumaria (mod 34), which
also carries ubigeo. Households are weighted by factornd07 = round(factor07*mieperho)
(person weight), exactly as INEI does.

VALIDATION: prints the national + urban/rural weighted mean ipcr_0 per year so it
can be checked against INEI's published "ingreso real per cápita".

Outputs (datasets/):
  income_real_district_<yA>_<yB>.csv   real pc income by district, both years + change
  income_real_province_<yA>_<yB>.csv   same by province
  income_real_national.csv             national + urban/rural means (validation)

Run:  python dataset_income.py            # default 2021 vs 2025
      python dataset_income.py 2019 2025
"""
from __future__ import annotations

import sys
import glob
import os
import re
import zipfile
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
METH = RAW / "_methodology_2025"
OUTDIR = ROOT / "datasets"

DEFLACTORES = METH / "deflactores_base2025_new.dta"   # i00..i08 by (aniorec,dpto), base 2025
DESPACIAL = METH / "despacial_ldnew.dta"              # ld by dominioA (17 domains)

# ipcr_0 income components, grouped exactly as INEI's do-file (all over the same
# denominator 12*mieperho*ld*i00). Missing columns in a given year are treated as 0
# (mirrors INEI's `recode ... (.=0)`).
INCOME_COMPONENTS = [
    # ipcr_2 trabajo principal
    "ingbruhd", "ingindhd",
    # ipcr_3 trabajo secundario
    "insedthd", "ingseihd", "insedthd1",
    # ipcr_4 pago en especie / autoconsumo
    "pagesphd", "paesechd", "ingauthd", "isecauhd", "paesechd1",
    # ipcr_5 extraordinario
    "ingexthd",
    # ipcr_7 / ipcr_8 transferencias
    "ingtrahd", "ingtexhd",
    # ipcr_16 renta
    "ingrenhd",
    # ipcr_17 extraordinario / otros
    "ingoexhd", "gru13hd3", "gru23hd3", "gru33hd3", "gru43hd3", "gru53hd3",
    "gru63hd3", "gru73hd3", "gru83hd3", "gru24hd", "gru44hd", "gru54hd",
    "gru74hd", "gru84hd", "gru14hd5",
    # ipcr_18 alquiler imputado  (note ga04hd enters NEGATIVE)
    "ia01hd", "gru34hd", "gru64hd",
    # ipcr_19 donacion publica
    "gru13hd1", "sig24", "gru23hd1", "gru33hd1", "gru43hd1", "gru53hd1",
    "gru63hd1", "gru73hd1", "gru83hd1", "gru14hd3", "sig26", "sig28",
    # ipcr_20 donacion privada
    "gru13hd2", "ig06hd", "gru23hd2", "gru33hd2", "gru43hd2", "gru53hd2",
    "gru63hd2", "ig08hd", "gru73hd2", "gru83hd2", "gru14hd4",
    "sg42d", "sg42d1", "sg42d2", "sg42d3",
]
NEGATIVE = ["ga04hd"]   # subtracted in ipcr_18


def _extract_canonical(year: int) -> str:
    """Extract the canonical sumaria-YYYY.dta (NOT the -12g variant) from the zip."""
    z = RAW / "_zips" / f"{ec.YEAR_CODE[year]}-Modulo34.zip"
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(z) as zf:
        for m in zf.namelist():
            if m.lower().endswith(".dta"):
                try:
                    zf.extract(m, tmp)
                except Exception:                       # noqa: BLE001
                    continue
    fs = glob.glob(os.path.join(tmp, "**", "*.dta"), recursive=True)
    exact = [f for f in fs if re.fullmatch(rf"sumaria-{year}\.dta", os.path.basename(f).lower())]
    if exact:
        return exact[0]
    canon = [f for f in fs if not re.search(r"-12g?\.dta$", os.path.basename(f).lower())]
    return max(canon or fs, key=os.path.getsize)


def _read_dta_robust(path):
    """Lee .dta robusto a Stata v110 (anios viejos): pyreadstat primero, pandas como fallback."""
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(path), encoding="latin1")
    except Exception:
        df = pd.read_stata(path, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def _cols_robust(path):
    """Columnas de un .dta sin cargarlo entero (robusto a v110)."""
    try:
        import pyreadstat
        _, meta = pyreadstat.read_dta(str(path), encoding="latin1", metadataonly=True)
        return [c.lower() for c in meta.column_names]
    except Exception:
        return [c.lower() for c in pd.read_stata(path, convert_categoricals=False).columns]


def _canon_sumaria(year: int) -> str:
    """Path to canonical sumaria-YYYY.dta. Validates that the raw file is the
    canonical one (has gru12hd1); if it is the -12g variant, re-extracts."""
    p = RAW / "sumaria" / f"enaho-{year}-34.dta"
    if p.exists():
        if "gru12hd1" in _cols_robust(p):
            return str(p)
        print(f"  [{year}] raw sumaria is the -12g variant - re-extracting canonical")
    return _extract_canonical(year)


def real_income(year: int) -> pd.DataFrame:
    """Return per-household df with ipcr_0 (real pc monthly income, base-2025 Lima)."""
    df = _read_dta_robust(_canon_sumaria(year))
    df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)

    # geography
    df["dpto"] = df["ubigeo"].str[:2].astype(int)
    df.loc[df["dpto"] == 7, "dpto"] = 15            # Callao -> Lima for deflation
    est = pd.to_numeric(df["estrato"], errors="coerce")
    dom = pd.to_numeric(df["dominio"], errors="coerce")
    est = est.where(dom != 8, 1)                    # estrato=1 if Lima Metro
    df["area"] = np.where(est < 6, 1, 2)            # 1 urbana, 2 rural

    # dominioA (17 domains) per INEI do-file
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

    # deflators
    defl = pd.read_stata(DEFLACTORES, convert_categoricals=False)
    defl.columns = [c.lower() for c in defl.columns]
    defl = defl[defl["aniorec"] == year][["dpto", "i00"]]
    desp = pd.read_stata(DESPACIAL, convert_categoricals=False)
    desp.columns = [c.lower() for c in desp.columns]
    df = df.merge(defl, on="dpto", how="left").merge(desp, on="dominioa", how="left",
                                                     suffixes=("", "_sp"))
    df["ld"] = df["ld_sp"] if "ld_sp" in df else df["ld"]   # use despacial ld

    # numerator = sum of income components (missing -> 0), minus ga04hd
    present = [c for c in INCOME_COMPONENTS if c in df.columns]
    missing = [c for c in INCOME_COMPONENTS if c not in df.columns]
    num = df[present].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    for c in NEGATIVE:
        if c in df.columns:
            num = num - pd.to_numeric(df[c], errors="coerce").fillna(0)
    if missing:
        print(f"  [{year}] note: {len(missing)} income components absent -> treated 0: "
              f"{', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")

    denom = 12 * df["mieperho"] * df["ld"] * df["i00"]
    df["ipcr_0"] = num / denom
    df["factornd07"] = (df["factor07"] * df["mieperho"]).round()
    df["persons"] = df["factor07"] * df["mieperho"]
    df["year"] = year
    return df.dropna(subset=["ipcr_0", "factornd07"])


def wmean(d: pd.DataFrame, val="ipcr_0", w="factornd07") -> float:
    m = d[val].notna() & d[w].notna()
    return float(np.average(d.loc[m, val], weights=d.loc[m, w]))


def aggregate(df: pd.DataFrame, key: str) -> pd.DataFrame:
    g = df.groupby(key).apply(
        lambda d: pd.Series({
            "real_pc_income": wmean(d),
            "persons": d["persons"].sum(),
            "n_hh": len(d),
        }), include_groups=False).reset_index()
    return g


def main():
    yA, yB = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) >= 3 else (2021, 2025)
    OUTDIR.mkdir(exist_ok=True)
    print(f"Building REAL per-capita income (base-2025 Lima soles): {yA} vs {yB}\n")

    dfs = {y: real_income(y) for y in (yA, yB)}

    # national validation
    val_rows = []
    for y in (yA, yB):
        d = dfs[y]
        nat = wmean(d)
        urb = wmean(d[d.area == 1]); rur = wmean(d[d.area == 2])
        val_rows.append({"year": y, "real_pc_income_national": round(nat, 1),
                         "urban": round(urb, 1), "rural": round(rur, 1),
                         "population": round(d["persons"].sum())})
        print(f"  {y}: national S/{nat:,.1f}/mes  | urban S/{urb:,.1f}  rural S/{rur:,.1f}")
    val = pd.DataFrame(val_rows)
    val.to_csv(OUTDIR / "income_real_national.csv", index=False)
    ch = 100 * (val_rows[1]["real_pc_income_national"] / val_rows[0]["real_pc_income_national"] - 1)
    print(f"\n  National real income change {yA}->{yB}: {ch:+.1f}%  "
          f"(constant {yB} soles, a precios de Lima)")

    # district & province
    for key, name, slc in [("ubigeo", "district", None), ("prov", "province", None)]:
        for y in (yA, yB):
            dfs[y]["prov"] = dfs[y]["ubigeo"].str[:4]
        gA = aggregate(dfs[yA], key).rename(columns={"real_pc_income": f"income_{yA}",
                                                     "persons": f"pop_{yA}", "n_hh": f"nhh_{yA}"})
        gB = aggregate(dfs[yB], key).rename(columns={"real_pc_income": f"income_{yB}",
                                                     "persons": f"pop_{yB}", "n_hh": f"nhh_{yB}"})
        m = gA.merge(gB, on=key, how="outer")
        m["chg_pct"] = 100 * (m[f"income_{yB}"] / m[f"income_{yA}"] - 1)
        m["chg_soles"] = m[f"income_{yB}"] - m[f"income_{yA}"]
        out = OUTDIR / f"income_real_{name}_{yA}_{yB}.csv"
        m.sort_values("chg_pct").to_csv(out, index=False)
        print(f"  wrote {name}: {len(m)} units -> {out.name}")

    print("\nDone. National table = datasets/income_real_national.csv")


if __name__ == "__main__":
    main()
