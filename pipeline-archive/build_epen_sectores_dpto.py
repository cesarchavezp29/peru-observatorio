"""
build_epen_sectores_dpto.py
===========================
Composicion sectorial del empleo por DEPARTAMENTO (EPEN 2025, microdatos, ponderado),
colapsada a 6 macro-sectores. Muestra el gradiente de transformacion estructural:
sierra/selva agropecuarias vs costa/urbana de servicios.

Out: datasets/epen_sectores_dpto_2025.csv (depto x macro-sector, % de ocupados)
"""
from __future__ import annotations
from pathlib import Path
import glob
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_sectores_dpto_2025.csv"
CODE = 1001  # 2025 Dpto nacional
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
        6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
        11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
        16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
        21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali"}
MACRO = ["Agropecuario/pesca", "Mineria", "Manufactura", "Construccion", "Comercio", "Servicios"]


def macro(code):
    if 100 <= code < 400: return "Agropecuario/pesca"
    if 500 <= code < 1000: return "Mineria"
    if 1000 <= code < 4100: return "Manufactura"     # incl. electricidad/agua
    if 4100 <= code < 4400: return "Construccion"
    if 4500 <= code < 4800: return "Comercio"
    if 4900 <= code < 10000: return "Servicios"      # transporte, restaurantes, otros, publico
    return None


def main():
    f = glob.glob(str(RAW / f"{CODE}_*/*.csv"))[0]
    df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    for c in ["ocup300", "ccdd", "c208", "c309_cod", "fac300_anual"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    oc = df[(df["c208"] >= 14) & (df["ocup300"] == 1)].copy()
    oc["macro"] = oc["c309_cod"].apply(macro)
    oc = oc[oc["macro"].notna()]
    w = "fac300_anual"
    rows = []
    for dd, name in DPTO.items():
        g = oc[oc["ccdd"] == dd]
        if not g[w].sum():
            continue
        rec = {"ccdd": dd, "departamento": name}
        for m in MACRO:
            rec[m] = round(100 * g[g["macro"] == m][w].sum() / g[w].sum(), 1)
        rows.append(rec)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} deptos)")
    print(d.sort_values("Agropecuario/pesca", ascending=False)[["departamento"] + MACRO].to_string(index=False))


if __name__ == "__main__":
    main()
