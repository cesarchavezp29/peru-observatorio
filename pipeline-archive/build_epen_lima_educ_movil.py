"""
build_epen_lima_educ_movil.py
=============================
Ingreso laboral real (soles de 2001) por NIVEL EDUCATIVO, Lima Metropolitana, TRIMESTRE
MOVIL, desde los microdatos modernos (EPEN movil, region==1, codes 774-1037), 2022-2026.
Continua la serie legacy (que usaba p109a). Variable moderna = c366 (nivel educativo),
ingreso = ingtotp (perceptores >0). Deflactado con IPC Lima INEI (base 2001).

c366 -> grupos: prim (1-4), sec (5-6), sup_no_univ (7-8), sup_univ (9-12).
Out: datasets/epen_lima_educ_movil_2022_2026.csv
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
IPC = ROOT / "datasets" / "_ipc_lima_linked.csv"
OUT = ROOT / "datasets" / "epen_lima_educ_movil_2022_2026.csv"
MES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
       "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
# c366 (verificado en el Diccionario EPEN 2022): 1 sin nivel, 2 inicial, 3 prim inc,
# 4 prim comp, 5 sec inc, 6 sec comp, 7 basica especial, 8 sup no univ inc, 9 sup no univ
# comp, 10 sup univ inc, 11 sup univ comp, 12 maestria/doctorado. Mapea al p109a legacy:
# prim 1-4 (+7 basica especial), sec 5-6, sup_no_univ 8-9, sup_univ 10-12 (incl. postgrado).
EDU = {"prim": [1, 2, 3, 4, 7], "sec": [5, 6], "sup_no_univ": [8, 9], "sup_univ": [10, 11, 12]}


def parse_trim(label):
    toks = re.findall(r"(ene|feb|mar|abr|may|jun|jul|ago|set|sep|oct|nov|dic)", label.lower())
    yy = re.findall(r"(\d{2})\b", label)
    if len(toks) < 3 or not yy:
        return None
    return (2000 + int(yy[-1])) * 100 + MES[toks[2]]


def main():
    ipc = pd.read_csv(IPC).set_index("ym")["factor_to_2001soles"]
    man = pd.read_csv(MAN)
    mov = man[(man["code"] >= 774) & man["label"].str.contains("Trim", na=False)
              & ~man["label"].str.contains("Nacional", na=False)]
    rows = []
    for _, r in mov.iterrows():
        code = int(r["code"]); ek = parse_trim(r["label"])
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs or ek is None or ek not in ipc.index:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        if not {"ocup300", "c366", "ingtotp", "region"}.issubset(df.columns):
            continue
        w = next((c for c in df.columns if re.match(r"^fa_", c)), None)
        if not w:
            continue
        for c in ["ocup300", "c366", "ingtotp", w]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        oc = df[(df["region"] == 1) & (df["ocup300"] == 1) & (df["ingtotp"] > 0) & df["ingtotp"].notna()]
        fac = ipc.get(ek)
        rec = {"ym": ek}
        for nm, codes in EDU.items():
            gg = oc[oc["c366"].isin(codes)]
            rec[f"ing_real_{nm}"] = round((gg[w] * gg["ingtotp"]).sum() / gg[w].sum() * fac) if gg[w].sum() else np.nan
        rows.append(rec)
    d = pd.DataFrame(rows).drop_duplicates("ym").sort_values("ym")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} | {len(d)} trimestres")
    print(d.tail(4).to_string(index=False))


if __name__ == "__main__":
    main()
