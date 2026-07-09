"""
fig_epen_heatmap_sector_dpto.py
===============================
Heatmap de INFORMALIDAD por SECTOR x DEPARTAMENTO (EPEN 2025, microdatos, ponderado).
Filas = departamentos (ordenados por informalidad total), columnas = 6 macro-sectores;
color = % de empleo informal (informal_p). Celdas con <40 obs quedan en blanco.

Out: figures/12_mapas/fig_epen_heatmap_sector_dpto.{pdf,png}
     datasets/epen_informal_sector_dpto_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
FIG = ROOT / "figures" / "12_mapas"; FIG.mkdir(parents=True, exist_ok=True)
fs.use()
SEQ_R = LinearSegmentedColormap.from_list("seqr", ["#eaf0f6", "#f0d3dc", "#d98aa3", fs.CRANBERRY])
MACRO = ["Agropecuario", "Mineria", "Manufactura", "Construccion", "Comercio", "Servicios"]
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho", 6: "Cajamarca",
        7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco", 11: "Ica", 12: "Junin",
        13: "La Libertad", 14: "Lambayeque", 15: "Lima", 16: "Loreto", 17: "Madre de Dios",
        18: "Moquegua", 19: "Pasco", 20: "Piura", 21: "Puno", 22: "San Martin", 23: "Tacna",
        24: "Tumbes", 25: "Ucayali"}


def macro(code):
    if 100 <= code < 400: return "Agropecuario"
    if 500 <= code < 1000: return "Mineria"
    if 1000 <= code < 4100: return "Manufactura"
    if 4100 <= code < 4400: return "Construccion"
    if 4500 <= code < 4800: return "Comercio"
    if 4900 <= code < 10000: return "Servicios"
    return None


def main():
    f = glob.glob(str(RAW / "1001_*/*.csv"))[0]
    df = pd.read_csv(f, encoding="latin-1", low_memory=False)
    df.columns = [c.strip().strip('"').lower() for c in df.columns]
    for c in ["ocup300", "ccdd", "c208", "c309_cod", "informal_p", "fac300_anual"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    oc = df[(df["c208"] >= 14) & (df["ocup300"] == 1)].copy()
    oc["macro"] = oc["c309_cod"].apply(macro)
    oc = oc[oc["macro"].notna()]
    w = "fac300_anual"
    M = np.full((len(DPTO), len(MACRO)), np.nan)
    tot = {}
    for i, (dd, name) in enumerate(DPTO.items()):
        g = oc[oc["ccdd"] == dd]
        if not len(g):
            continue
        tot[dd] = 100 * (g[w] * (g["informal_p"] == 1)).sum() / g[w].sum()
        for j, m in enumerate(MACRO):
            c = g[g["macro"] == m]
            if len(c) >= 40:
                M[i, j] = 100 * (c[w] * (c["informal_p"] == 1)).sum() / c[w].sum()
    order = sorted([i for i, dd in enumerate(DPTO) if dd in tot], key=lambda i: tot[list(DPTO)[i]])
    names = [DPTO[list(DPTO)[i]] for i in order]
    M = M[order]
    pd.DataFrame(M, index=names, columns=MACRO).to_csv(ROOT / "datasets" / "epen_informal_sector_dpto_2025.csv")

    fig, ax = plt.subplots(figsize=(9.2, 9.5))
    norm = Normalize(40, 100)
    im = ax.imshow(M, cmap=SEQ_R, norm=norm, aspect="auto")
    ax.set_xticks(range(len(MACRO))); ax.set_xticklabels(MACRO, rotation=30, ha="right", fontsize=9.5)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8.5)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=7.4,
                        color="white" if M[i, j] > 78 else "#222")
    ax.set_xticks(np.arange(-.5, len(MACRO), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(names), 1), minor=True)
    ax.grid(which="minor", color="white", lw=1.2); ax.tick_params(which="minor", length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02); cb.set_label("% empleo informal", fontsize=9.5); cb.outline.set_visible(False)
    ax.set_title("Empleo informal por sector y departamento  -  EPEN 2025", fontsize=12.5, fontweight="semibold", pad=12)
    fs.source(fig, "EPEN 2025 (microdatos INEI), informal_p. Celdas con <40 obs en blanco. Deptos ordenados por "
              "informalidad total.\nEl agro es ~95% informal en todo el pais; los servicios y la manufactura "
              "concentran la variacion (formales en Lima/costa, informales en la sierra).", x=0.01, y=0.005)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig_epen_heatmap_sector_dpto.pdf"); fig.savefig(FIG / "fig_epen_heatmap_sector_dpto.png", dpi=160)
    print("wrote", FIG / "fig_epen_heatmap_sector_dpto.png")


if __name__ == "__main__":
    main()
