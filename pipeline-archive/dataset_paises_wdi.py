"""
dataset_paises_wdi.py  -  Peru vs vecinos (Banco Mundial WDI)
=============================================================
Series comparables entre paises (las lineas de pobreza NACIONALES no son
comparables entre paises, cada una se define distinto):

  paises_gini_tiempo_wdi.csv     SI.POV.GINI  (Gini del ingreso, WDI)
  paises_pobreza685_wdi.csv      SI.POV.UMIC  (pobreza $6.85/dia 2017 PPP)

Formato: year x una columna por pais (Peru, Chile, Colombia, Bolivia, Ecuador,
Brasil, Mexico, Argentina). Fuente citada en el titulo del catalogo.

Run:  python dataset_paises_wdi.py
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "datasets"
COUNTRIES = {"PER": "Peru", "CHL": "Chile", "COL": "Colombia", "BOL": "Bolivia",
             "ECU": "Ecuador", "BRA": "Brasil", "MEX": "Mexico", "ARG": "Argentina"}
SERIES = {
    "SI.POV.GINI": "paises_gini_tiempo_wdi.csv",
    "SI.POV.UMIC": "paises_pobreza685_wdi.csv",
}


def fetch(indicator: str) -> pd.DataFrame:
    iso = ";".join(COUNTRIES)
    url = (f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}"
           f"?format=json&per_page=2000&date=2000:2025")
    with urlopen(url, timeout=120) as r:
        data = json.load(r)[1]
    rows = [{"year": int(d["date"]), "pais": COUNTRIES[d["countryiso3code"]],
             "valor": d["value"]} for d in data if d["value"] is not None]
    df = pd.DataFrame(rows).pivot_table(index="year", columns="pais", values="valor")
    return df.round(1).reset_index()


def main() -> None:
    for ind, fname in SERIES.items():
        df = fetch(ind)
        df.to_csv(OUT / fname, index=False, encoding="utf-8")
        last = df.dropna(subset=["Peru"]).iloc[-1]
        print(f"{fname}: {len(df)} anios, Peru ultimo dato {int(last['year'])} = {last['Peru']}")


if __name__ == "__main__":
    main()
