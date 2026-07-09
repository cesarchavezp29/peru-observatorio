"""
build_epen_ciudades.py
======================
Indicadores de mercado laboral por CIUDAD, EPEN BD Ciudades Anual 2025 (code 999, microdatos
ponderados). El mapeo codciudad->ciudad es OFICIAL: sale de las etiquetas de valor embebidas
en la version SPSS (.sav) del archivo (variable CODCIUDAD), guardado en
datasets/epen_codciudad_dict.csv. El .csv del INEI no trae etiquetas; el .sav si.

NB: el dato tiene 50 codciudad distintos pero INEI solo etiqueta 27 (las "ciudades
principales" del informe tecnico). Los 23 sin etiqueta quedan como "Ciudad <cod>" y se marcan
oficial=0; el analisis principal usa los 27 oficiales (oficial=1).

Indicadores (ocupados/PEA 14+, ponderado fac300_anual):
  desempleo = ocup300==2 / PEA(1,2);  informalidad = informal_p==1 / ocupados
  ingreso   = ingtotp medio de ocupados remunerados (excl. TFNR c310 in {4,8})

Out: datasets/epen_ciudades_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIC = ROOT / "datasets" / "epen_codciudad_dict.csv"
OUT = ROOT / "datasets" / "epen_ciudades_2025.csv"


def main():
    dmap = dict(pd.read_csv(DIC).itertuples(index=False, name=None))
    # nombres INFERIDOS para los 23 sin etiqueta INEI (estructural: depto por posicion del
    # codigo, provincia por orden, tamano PET). Ver build_epen_ciudades_inferir.py / README.
    inf = pd.read_csv(ROOT / "datasets" / "epen_codciudad_inferred.csv")
    imap = {int(r.cod): (r.ciudad_inferida, r.conf) for r in inf.itertuples()}
    f = glob.glob(str(ROOT / "raw" / "epen_inei" / "999_*/*.csv"))[0]
    df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    for c in ["ocup300", "c208", "ingtotp", "informal_p", "codciudad", "fac300_anual", "c310"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    w = "fac300_anual"
    rows = []
    for cod, g in df[df.c208 >= 14].groupby("codciudad"):
        cod = int(cod)
        pea = g[g.ocup300.isin([1, 2])]
        oc = g[g.ocup300 == 1]
        rem = oc[oc.ingtotp.notna() & (oc.ingtotp > 0) & ~oc.c310.isin([4, 8])]
        des = 100 * (pea[w] * (pea.ocup300 == 2)).sum() / pea[w].sum() if pea[w].sum() else np.nan
        inf = 100 * (oc[w] * (oc.informal_p == 1)).sum() / oc[w].sum() if oc[w].sum() else np.nan
        ing = (rem[w] * rem.ingtotp).sum() / rem[w].sum() if rem[w].sum() else np.nan
        if cod in dmap:
            ciudad, fuente, conf = dmap[cod], "oficial", "OFICIAL"
        elif cod in imap:
            ciudad, fuente, conf = imap[cod][0], "inferida", imap[cod][1]
        else:
            ciudad, fuente, conf = f"Ciudad {cod}", "sin_id", "—"
        rows.append({
            "codciudad": cod,
            "ciudad": ciudad,
            "fuente": fuente,
            "confianza": conf,
            "oficial": int(cod in dmap),
            "pet": round(g[w].sum()),
            "n": len(g),
            "desempleo": round(des, 1),
            "informalidad": round(inf, 1),
            "ingreso": round(ing),
        })
    r = pd.DataFrame(rows).sort_values("pet", ascending=False)
    r.to_csv(OUT, index=False, encoding="utf-8")
    off = r[r.oficial == 1]
    print(f"Wrote {OUT} | {len(r)} codciudad ({off.oficial.sum()} oficiales con nombre, "
          f"{len(r)-len(off)} sin etiqueta INEI)")
    print(off[["ciudad", "pet", "desempleo", "informalidad", "ingreso"]].to_string(index=False))


if __name__ == "__main__":
    main()
