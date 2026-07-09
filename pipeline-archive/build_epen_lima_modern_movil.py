"""
build_epen_lima_modern_movil.py
===============================
EPEN Lima Metropolitana TRIMESTRE MOVIL desde microdatos modernos (codes 774-1037, los
"Trim_Mes_Mes_Mes" con region==1 = Lima Metropolitana), 2022-2026. Continua la EPE legacy
con la MISMA frecuencia (trimestre movil), NO anual.

Verificado: desempleo de estos archivos reproduce INEI/BCRP PN38063GM a 0.00pp.
Vars: ocup300 (empleo 1/2/3/4), c207 (sexo 1H/2M), c208 (edad), ingtotp (ingreso principal),
fa_<trim><yy> (factor de expansion trimestral). region==1 = Lima Metropolitana.

Out: datasets/epen_lima_movil_modern_2022_2026.csv (una fila por trimestre movil)
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
MAN = RAW / "_epen_manifest.csv"
OUT = ROOT / "datasets" / "epen_lima_movil_modern_2022_2026.csv"
MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
       "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def parse_trim(label):
    toks = re.findall(r"(ene|feb|mar|abr|may|jun|jul|ago|set|sep|oct|nov|dic)", label.lower())
    yy = re.findall(r"(\d{2})\b", label)
    if len(toks) < 3 or not yy:
        return None
    em = MES[toks[2]]; year = 2000 + int(yy[-1])
    # end-month key (yyyymm); the 3-month window ENDS in toks[2]
    return year * 100 + em


def main():
    m = pd.read_csv(MAN)
    mov = m[(m["code"] >= 774) & m["label"].str.contains("Trim", na=False)
            & ~m["label"].str.contains("Nacional", na=False)]
    rows = []
    for _, r in mov.iterrows():
        code = int(r["code"]); ek = parse_trim(r["label"])
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
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
            # PET = denominador restringido a condicion de actividad valida (1-4). Sin esto, los
            # registros ocup300 NaN/0 inflan la PET y hunden la actividad ~5pp en algunos trim.
            pet = (sub[w] * sub["ocup300"].isin([1, 2, 3, 4])).sum()
            return round(100 * (sub[w] * sub["ocup300"].isin([1, 2])).sum() / pet, 2) if pet else np.nan
        oc = g[g["ocup300"] == 1]
        perc = oc[oc.get("ingtotp", pd.Series(np.nan, index=oc.index)).notna() & (oc.get("ingtotp", 0) > 0)] if "ingtotp" in g else oc.iloc[0:0]
        ing = round((perc[w] * perc["ingtotp"]).sum() / perc[w].sum()) if len(perc) and perc[w].sum() else np.nan
        # sector informal proxy (calibrado vs informal_p): c310 categoria, c317a tamano (<=5).
        # c310: 1 empleador, 2 indep, 3 asalariado, 4 TFNR, 6 trab.hogar, 7/8 otro.
        if "c310" in oc and "c317a" in oc:
            # c310 (dicc. EPEN): 1 empleador, 2 indep, 3 empleado/obrero, 4 ayudante negocio
            # familiar (TFNR), 5 ayudante empleo familiar, 6 trab. hogar, 7 aprendiz remun,
            # 8 practicante sin remun. Informales por naturaleza: 2,4,5,6,8; por tamano (<=5): 1,3,7.
            small = oc["c317a"] <= 5
            informal = oc["c310"].isin([2, 4, 5, 6, 8]) | (oc["c310"].isin([1, 3, 7]) & small)
            inf = round(100 * (oc[w] * informal).sum() / oc[w].sum(), 2) if oc[w].sum() else np.nan
        else:
            inf = np.nan
        # estructura ocupacional (c310): 1 empleador, 2 indep, 3 asalariado, 4 TFNR, 6 trab.hogar
        def sh(cats):
            return round(100 * (oc[w] * oc["c310"].isin(cats)).sum() / oc[w].sum(), 2) if "c310" in oc and oc[w].sum() else np.nan
        # subempleo visible (horas): whorat (total horas trabajadas) <35 & p209h==1 (desea y
        # disponible a trabajar mas). NB: whorat (EPEN) tiene menos gente <35h que p209t (EPE),
        # por eso el subempleo visible da ~3pp menos en el empalme -- quiebre metodologico real.
        if "whorat" in oc and "p209h" in oc:
            vis = (oc["whorat"] < 35) & (oc["p209h"] == 1)
            subv = round(100 * (oc[w] * vis).sum() / oc[w].sum(), 2) if oc[w].sum() else np.nan
        else:
            subv = np.nan
        # sobreempleo / sobre-jornada: > 48 h/sem (jornada legal); y horas medias
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
            "tasa_actividad": act(g), "tasa_actividad_h": act(g[g["c207"] == 1]), "tasa_actividad_m": act(g[g["c207"] == 2]),
            "tasa_informalidad": inf, "ing_nominal": ing,
            "asalariado": sh([3]), "independiente": sh([2]), "empleador": sh([1]), "trab_hogar": sh([6]),
            "sub_visible": subv, "sobreempleo": sobre, "horas_medias": hmed,
        })
    d = pd.DataFrame(rows).drop_duplicates("ym").sort_values("ym")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} | {len(d)} trimestres moviles | span {int(d.ym.min())}-{int(d.ym.max())}")
    print(d[["ym", "tasa_desempleo", "tasa_desempleo_m", "tasa_actividad", "ing_nominal"]].to_string(index=False))


if __name__ == "__main__":
    main()
