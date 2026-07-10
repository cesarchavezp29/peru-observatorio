"""Produce las series BCRP verificadas: desempleo Lima, IPC 2009 y el empalme.

Series REIDENTIFICADAS contra lo committeado por solape exacto (2026-07-10):
  PN38063GM  Desempleo Lima Metropolitana, promedio movil 3m  (diff 0 en 260 meses)
  PN01270PM  IPC Lima Metropolitana, indice 2009=100          (diff <1e-4)
NO se refrescan aqui (congeladas con nota, cosecha no reidentificable):
_ipc_lima_linked (su continuacion 2022+ no proviene de PN01270PM ni del
encadenado de PN01276PM — verificado, deriva 6 puntos), _bcrp_lima_2026
(sub-series por sexo/edad sin codigo BCRP identificable) y _bcrp_subempleo.
Congelar honesto vence a refrescar a ciegas.

Run:
  python pipeline/build_bcrp.py                      # escribe (extiende series)
  python pipeline/build_bcrp.py --check-against data/datasets   # valida solape
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
MES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7,
       "Ago": 8, "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}
DESEMPLEO = "PN38063GM"
IPC = "PN01270PM"


def fetch(code: str) -> pd.Series:
    url = (f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{code}"
           f"/json/2000-1/2026-12")
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=90) as r:
        d = json.load(r)
    s = pd.Series({p["name"]: float(p["values"][0]) for p in d["periods"]
                   if p["values"][0] not in (None, "n.d.")})
    s.index = [int(p.split(".")[1]) * 100 + MES[p.split(".")[0]] for p in s.index]
    return s[~s.index.duplicated()].sort_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS

    des = fetch(DESEMPLEO)
    # el CSV committeado escribe septiembre como "Sep" (no el "Set" del BCRP)
    inv = {v: k for k, v in MES.items() if k != "Set"}
    des_out = pd.DataFrame({"period": [f"{inv[ym % 100]}.{ym // 100}" for ym in des.index],
                            "value": des.values})
    des_out.to_csv(outdir / "_bcrp_desempleo_lima.csv", index=False)

    ipc = fetch(IPC)
    ipc_out = pd.DataFrame({"ym": ipc.index, "ipc": ipc.values.round(6)})
    ipc_out.to_csv(outdir / "_ipc_lima_2009base.csv", index=False)

    print(f"desempleo {len(des)} meses ({des.index.min()}-{des.index.max()}), "
          f"ipc {len(ipc)} meses")

    if a.check_against:
        ref_dir = Path(a.check_against)
        bad = 0
        for name, key in [("_bcrp_desempleo_lima.csv", "period"),
                          ("_ipc_lima_2009base.csv", "ym")]:
            ref = pd.read_csv(ref_dir / name)
            new = pd.read_csv(outdir / name)
            m = ref.merge(new, on=key, suffixes=("_ref", "_new"))
            if len(m) < len(ref) * 0.98:
                print(f"  FAIL {name}: solape insuficiente ({len(m)}/{len(ref)})")
                bad += 1
                continue
            for c in ref.columns:
                if c == key:
                    continue
                d = (pd.to_numeric(m[f"{c}_ref"], errors="coerce")
                     - pd.to_numeric(m[f"{c}_new"], errors="coerce")).abs().max()
                if pd.notna(d) and d > 1e-4:
                    print(f"  FAIL {name} col {c}: max diff {d}")
                    bad += 1
            ext = len(new) - len(m)
            print(f"  {name}: solape {len(m)} OK, serie extendida en {ext} periodos")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
