"""
fig_epen_lima_subempleo.py
==========================
Composicion de la PEA ocupada de Lima Metropolitana: adecuadamente empleada,
subempleo INVISIBLE (por ingresos) y subempleo VISIBLE (por horas),
trimestre movil 2001-2022. Area apilada (un solo plot).

Sources (honest mix, stated in footnote):
 - Subempleo VISIBLE = de microdatos EPE: ocupados 14+ con horas<35 que desean y estan
   disponibles para trabajar mas (p209t<35 & p209h==1). Definicion exacta, insumos validados.
 - Total subempleo / adecuado = serie OFICIAL INEI/BCRP (PN38062/61GM). El subempleo
   INVISIBLE (por ingresos) NO es reproducible a 0.00pp sin el ingreso minimo referencial
   de INEI, por eso se obtiene como residual: invisible = total_oficial - visible.

Out: figures/07_empleo/fig_epen_lima_subempleo.{pdf,png}
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "clean" / "epen_lima_panel.parquet"
BCRP = ROOT / "datasets" / "_bcrp_subempleo_lima.csv"
OUTD = ROOT / "figures" / "07_empleo"; OUTD.mkdir(parents=True, exist_ok=True)


def cdate(ts):
    y, m = ts // 100, ts % 100; cm = m + 1; cy = y
    if cm > 12: cm -= 12; cy += 1
    return pd.Timestamp(cy, cm, 15)


def endkey(ts):
    y, m = ts // 100, ts % 100; em = m + 2; ey = y
    if em > 12: em -= 12; ey += 1
    return ey * 100 + em


def main():
    p = pd.read_parquet(PANEL, columns=["trim_start", "edad", "ocu200", "horas", "desea_mas_horas", "w"])
    o = p[(p["edad"] >= 14) & (p["ocu200"] == 1)]
    rows = []
    for ts, g in o.groupby("trim_start"):
        tot = g["w"].sum()
        vis = g[(g["horas"] < 35) & (g["desea_mas_horas"] == 1)]["w"].sum()
        rows.append({"trim_start": int(ts), "ek": endkey(int(ts)), "sub_visible": 100 * vis / tot})
    d = pd.DataFrame(rows)
    b = pd.read_csv(BCRP)
    b["sub_total"] = 100 * b["subempleo_mil"] / b["pea_ocupada_mil"]
    b["adecuado"] = 100 * b["adecuado_mil"] / b["pea_ocupada_mil"]
    d = d.merge(b[["ym", "sub_total", "adecuado"]], left_on="ek", right_on="ym").sort_values("trim_start")
    d["sub_invisible"] = (d["sub_total"] - d["sub_visible"]).clip(lower=0)
    d["f"] = d["trim_start"].apply(cdate)

    fig, ax = fs.fig_ax()
    ax.stackplot(d["f"], d["adecuado"], d["sub_invisible"], d["sub_visible"],
                 colors=[fs.NAVY, fs.CRANBERRY, fs.GOLD], alpha=0.9,
                 labels=["Adecuadamente empleado", "Subempleo invisible (ingresos)", "Subempleo visible (horas)"])
    ax.legend(loc="lower center", ncol=3, fontsize=8.5, bbox_to_anchor=(0.5, -0.02))
    ax.set_ylabel("% de la PEA ocupada"); ax.set_xlabel(""); ax.set_ylim(0, 100); ax.margins(x=0)
    fs.source(fig,
              "EPE Lima Metropolitana y Callao. Subempleo VISIBLE de microdatos INEI (horas<35 y "
              "desea/disponible a trabajar mas); total y adecuado OFICIAL INEI/BCRP (PN38061/62GM).\n"
              "El subempleo INVISIBLE (por ingresos) cayo de ~40% a ~22% (2003-2014) con el alza del "
              "ingreso real; el visible (horas) se mantuvo ~13-20%. Invisible = total oficial - visible.",
              y=0.005)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(OUTD / "fig_epen_lima_subempleo.pdf")
    fig.savefig(OUTD / "fig_epen_lima_subempleo.png", dpi=150)
    print("wrote", OUTD / "fig_epen_lima_subempleo.png",
          f"| 2022 adecuado={d['adecuado'].iloc[-1]:.0f} inv={d['sub_invisible'].iloc[-1]:.0f} vis={d['sub_visible'].iloc[-1]:.0f}")


if __name__ == "__main__":
    main()
