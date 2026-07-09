"""
fig_trust_vote_pro.py - publication-quality trust vs 2nd-round vote
===================================================================
Two panels (2021, 2026). Points colored by who won the department, sized by the
electorate, OLS line with 95% CI band, haloed department labels.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"; FIG=ROOT/"figures"/"03_elecciones"; FIG.mkdir(parents=True,exist_ok=True)


def bubble_sizes(v):
    v = np.asarray(v, float)
    return 30 + 330 * np.sqrt(v / v.max())


def panel(ax, df, xcol, ycol, votecols, ylabel, leftwins_high):
    df = df.dropna(subset=[xcol, ycol]).copy()
    x, y = df[xcol].to_numpy(), df[ycol].to_numpy()
    elect = df[votecols].sum(axis=1)
    # color: navy = left/anti-establishment won, cranberry = Fujimori/right won
    left_won = (y > 50) if leftwins_high else (y < 50)
    colors = np.where(left_won, fs.CRANBERRY, fs.NAVY)

    ax.axhline(50, color=fs.GREY, ls=(0, (4, 4)), lw=1, zorder=1)
    ax.scatter(x, y, s=bubble_sizes(elect), c=colors, alpha=0.85,
               edgecolor="white", linewidth=1.1, zorder=5)
    slope, r, p = fs.ci_band(ax, x, y, color=fs.INK)

    fs.repel_labels(ax, x, y, [d.title() for d in df["department"]], fs=7.5)

    ax.set_xlabel("Confianza en instituciones políticas (%)")
    ax.set_ylabel(ylabel)
    pstar = "< 0.001" if p < 0.001 else f"= {p:.3f}"
    fs.statbox(ax, [f"pendiente = {slope:+.1f} pp", f"r = {r:+.2f}",
                    f"p {pstar}", f"n = {len(df)} deptos"],
               loc="upper right" if leftwins_high else "lower left")
    return slope, r, p


def main():
    fs.use()
    d21 = pd.read_csv(DATA / "trust_income_vote_dept_2021.csv")
    d26 = pd.read_csv(DATA / "trust_income_vote_dept_2026.csv")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14.5, 8.2))
    panel(a1, d21, "trust_pol", "castillo_pct", ["castillo", "keiko"],
          "Voto Castillo · Perú Libre (%)", leftwins_high=True)
    panel(a2, d26, "trust_pol", "keiko_pct", ["keiko", "juntos"],
          "Voto Keiko · Fuerza Popular (%)", leftwins_high=False)
    a1.set_title("2021  ·  izquierda gana donde se confía menos", loc="left", color=fs.INK)
    a2.set_title("2026  ·  la relación se diluye", loc="left", color=fs.INK)

    # shared legend
    from matplotlib.lines import Line2D
    leg = [Line2D([0], [0], marker="o", ls="", mfc=fs.CRANBERRY, mec="white", ms=10,
                  label="ganó la izquierda / outsider"),
           Line2D([0], [0], marker="o", ls="", mfc=fs.NAVY, mec="white", ms=10,
                  label="ganó Keiko / derecha")]
    fig.legend(handles=leg, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("Desconfianza en instituciones políticas y voto en segunda vuelta, por departamento",
                 fontsize=14, fontweight="semibold", x=0.5, y=1.02)
    fig.text(0.5, 0.965, "Confianza = % que confía (suficiente/bastante) en Congreso, partidos, "
             "Poder Judicial y gobierno regional · tamaño = nº de electores",
             ha="center", fontsize=10, color=fs.GREY)
    fs.source(fig, "Fuente: ENAHO Módulo 85 (INEI), 2021 y 2025 · resultados ONPE 2da vuelta "
              "(resultadosegundavuelta.onpe.gob.pe) · elaboración propia.")
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"fig_trust_vote_pro.{ext}", dpi=200, bbox_inches="tight")
    print("Saved figures/fig_trust_vote_pro.png/.pdf")


if __name__ == "__main__":
    main()
