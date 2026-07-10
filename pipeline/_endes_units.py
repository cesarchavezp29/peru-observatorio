"""Copia verbatim de ENAHO_ANALYSIS/scripts/endes_units.py (trampa acumulativa
2004-2008), con RAW parametrizado por ENDES_RAW (unico cambio de plomeria)."""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd

ENDES_CODE = {1996: 32, 2000: 35, 2004: 120, 2005: 150, 2006: 183, 2007: 194,
              2008: 209, 2009: 238, 2010: 260, 2011: 290, 2012: 323, 2013: 407,
              2014: 441, 2015: 504, 2016: 548, 2017: 605, 2018: 638, 2019: 691,
              2020: 739, 2021: 760, 2022: 786, 2023: 910, 2024: 968}

RAW = Path(os.environ.get("ENDES_RAW", "peru_raw/endes"))

_SRC = {2004: "2007_194", 2005: "2007_194", 2006: "2007_194", 2007: "2007_194",
        2008: "2008_209"}
for _y in range(2009, 2025):
    _SRC[_y] = f"{_y}_{ENDES_CODE[_y]}"


def years(y0=2004, y1=2024):
    return [y for y in range(y0, y1 + 1) if y in _SRC]


def dir_for(y: int) -> Path:
    return RAW / _SRC[y]


def cmc_year(s) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return 1900 + ((v - 1) // 12)


def true_year_mask(df: pd.DataFrame, y: int, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(True, index=df.index)
    return cmc_year(df[col]).eq(y)
