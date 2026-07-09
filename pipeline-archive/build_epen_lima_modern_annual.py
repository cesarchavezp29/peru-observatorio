"""
build_epen_lima_modern_annual.py
================================
Indicadores anuales de Lima Metropolitana desde los MICRODATOS del EPEN moderno
(codes 804/888/949/1015 = "15 Lima incl. Callao", filtro division_lima==1), 2022-2025.
Mismas definiciones que la serie legacy, calculadas de microdatos (NO de agregados BCRP).

Variables EPEN moderno (verificadas): ocup300 = condicion de actividad (1 ocupado, 2 desoc
abierto, 3 desoc oculto, 4 noPEA), c207 = sexo (1 H, 2 M), c208 = edad, informal_p (1 informal,
2 formal), ingtrabw = ingreso por trabajo, fac300_anual = factor de expansion anual.

Out: datasets/epen_lima_modern_annual_2022_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
IPC = ROOT / "datasets" / "_ipc_lima_linked.csv"
OUT = ROOT / "datasets" / "epen_lima_modern_annual_2022_2025.csv"
CODES = {2022: 804, 2023: 888, 2024: 949, 2025: 1015}


def load(code):
    f = glob.glob(str(RAW / f"{code}_*/*.csv"))[0]
    df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    for c in ["ocup300", "division_lima", "fac300_anual", "informal_p", "ingtrabw", "c207", "c208"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[df["division_lima"] == 1]


def main():
    ipc = pd.read_csv(IPC).set_index("ym")["factor_to_2001soles"]
    # annual deflator factor = mean of that year's 12 monthly factors
    def yfac(y):
        fs = [ipc.get(y * 100 + m) for m in range(1, 13) if (y * 100 + m) in ipc.index]
        return np.mean(fs) if fs else np.nan
    rows = []
    for y, code in CODES.items():
        g = load(code); w = "fac300_anual"
        pet = g[g["c208"] >= 14]
        def des(sub):
            pea = (sub[w] * sub["ocup300"].isin([1, 2])).sum()
            return round(100 * (sub[w] * (sub["ocup300"] == 2)).sum() / pea, 2) if pea else np.nan
        def act(sub):
            petd = (sub[w] * sub["ocup300"].isin([1, 2, 3, 4])).sum()  # PET valida (excluye ocup300 NaN/0)
            return round(100 * (sub[w] * sub["ocup300"].isin([1, 2])).sum() / petd, 2) if petd else np.nan
        oc = pet[pet["ocup300"] == 1]
        inf = round(100 * (oc[w] * (oc["informal_p"] == 1)).sum() / oc[w].sum(), 1) if oc[w].sum() else np.nan
        perc = oc[oc["ingtrabw"].notna() & (oc["ingtrabw"] > 0)]
        ing = (perc[w] * perc["ingtrabw"]).sum() / perc[w].sum()
        rows.append({
            "anio": y, "ym": y * 100 + 7,
            "tasa_desempleo": des(pet),
            "tasa_desempleo_h": des(pet[pet["c207"] == 1]),
            "tasa_desempleo_m": des(pet[pet["c207"] == 2]),
            "tasa_desempleo_joven": des(pet[(pet["c208"] >= 14) & (pet["c208"] <= 24)]),
            "tasa_desempleo_adulto": des(pet[(pet["c208"] >= 25) & (pet["c208"] <= 44)]),
            "tasa_desempleo_mayor": des(pet[pet["c208"] >= 45]),
            "tasa_actividad": act(pet),
            "tasa_actividad_h": act(pet[pet["c207"] == 1]),
            "tasa_actividad_m": act(pet[pet["c207"] == 2]),
            "tasa_informalidad": inf,
            "ing_nominal": round(ing),
            "ing_real_2001": round(ing * yfac(y)),
        })
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT}")
    print(d.to_string(index=False))


if __name__ == "__main__":
    main()
