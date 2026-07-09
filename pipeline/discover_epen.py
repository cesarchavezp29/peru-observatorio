"""Descubre y descarga los codigos EPEN nuevos del INEI (mensual).

INEI publica cada trimestre movil como un codigo nuevo sin anuncio. Se prueba
la ventana de codigos encima del maximo local y perudata.epen descarga los que
existan (labels desde el zip, verificados por apertura). Los 404 son rapidos.

Run:  PERUDATA_DIR=... python pipeline/discover_epen.py
"""
from __future__ import annotations

import os
from pathlib import Path

from perudata import epen

WINDOW = 40


def main() -> None:
    raw = Path(os.environ.get("PERUDATA_DIR", "peru_raw")) / "epen"
    codes = [int(d.name.split("_")[0]) for d in raw.iterdir()
             if d.is_dir() and d.name.split("_")[0].isdigit()] if raw.exists() else []
    start = (max(codes) if codes else 1037) + 1
    print(f"probing EPEN codes {start}..{start + WINDOW - 1} (max local: {start - 1})")
    got = epen.download(list(range(start, start + WINDOW)))
    print(f"nuevos datasets: {len(got)}")


if __name__ == "__main__":
    main()
