"""
fig_map_income.py - real income maps, levels + change (province)
================================================================
Three panels:
  Row 1:  income LEVEL 2021   |   income LEVEL 2025   (shared sequential scale)
  Row 2:  CHANGE 2021 -> 2025  (diverging, centered, bottom-middle)

Real per-capita monthly income, constant 2025 Lima soles, INEI methodology
(see dataset_income.py / validate_gasto.py). Mapped by PROVINCE.

Colorbars are drawn by geopandas from the actual plotted data (legend=True), so
the bar always matches the polygon colors. Change values are clipped to a robust
range for display and low-sample provinces are hatched.

Inputs : datasets/income_real_province_2021_2025.csv  (run dataset_income.py first)
Outputs: figures/fig_income_levels_change_2021_2025.pdf/.png
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm, Normalize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
FIG=ROOT/"figures"/"01_ingreso_pobreza"; FIG.mkdir(parents=True,exist_ok=True)
SHP = Path("D:/Shining Path and Geographic/Final Results/Figures/"
           "Limite Distrital INEI 2025 CPV.shp")
MIN_HH = 30
YA, YB = 2021, 2025


def main():
    FIG.mkdir(exist_ok=True)
    prov = pd.read_csv(DATA / f"income_real_province_{YA}_{YB}.csv", dtype={"prov": str})
    prov["prov"] = prov["prov"].str.zfill(4)
    prov["nhh_min"] = prov[[f"nhh_{YA}", f"nhh_{YB}"]].min(axis=1)

    g = gpd.read_file(SHP)
    g["UBIGEO"] = g["UBIGEO"].astype(str).str.zfill(6)
    g["prov"] = g["UBIGEO"].str[:4]
    gp = g.dissolve(by="prov")[["geometry"]].reset_index().merge(prov, on="prov", how="left")

    # shared level scale (robust, both years)
    lv = pd.concat([gp[f"income_{YA}"], gp[f"income_{YB}"]]).dropna()
    lvmin, lvmax = np.percentile(lv, [3, 97])
    lnorm = Normalize(vmin=float(lvmin), vmax=float(lvmax))

    # change scale (robust, symmetric); clip for display
    clim = float(np.nanpercentile(np.abs(gp["chg_pct"].dropna()), 90))
    clim = min(max(round(clim / 5) * 5, 15), 40)
    gp["chg_disp"] = gp["chg_pct"].clip(-clim, clim)
    cnorm = TwoSlopeNorm(vmin=-clim, vcenter=0, vmax=clim)

    fig = plt.figure(figsize=(13, 14))
    gs = fig.add_gridspec(2, 4, hspace=0.02, wspace=0.05)
    ax1 = fig.add_subplot(gs[0, 0:2])
    ax2 = fig.add_subplot(gs[0, 2:4])
    ax3 = fig.add_subplot(gs[1, 1:3])

    # distinct style so "not sampled" can't be mistaken for low income
    miss = {"color": "#cccccc", "edgecolor": "0.35", "hatch": "xxxx",
            "label": "not sampled that year"}
    # levels (share scale; each gets a matching colorbar via legend=True)
    for ax, yr in [(ax1, YA), (ax2, YB)]:
        gp.plot(ax=ax, column=f"income_{yr}", cmap="YlGnBu", norm=lnorm,
                edgecolor="white", linewidth=0.15, legend=True, missing_kwds=miss,
                legend_kwds={"shrink": 0.55, "label": "S/ per capita / month",
                             "orientation": "vertical"})
        ax.set_title(f"Real income level — {yr}", fontsize=12)
        nmiss = int(gp[f"income_{yr}"].isna().sum())
        if nmiss:
            ax.text(0.5, -0.03, f"{nmiss} province not sampled by ENAHO {yr} "
                    f"(Purús, Ucayali — remote Amazon)", transform=ax.transAxes,
                    ha="center", fontsize=7.5, color="0.3")
        ax.axis("off")

    # change (centered, bottom)
    gp.plot(ax=ax3, column="chg_disp", cmap="RdBu", norm=cnorm,
            edgecolor="white", linewidth=0.15, legend=True, missing_kwds=miss,
            legend_kwds={"shrink": 0.55,
                         "label": f"% change {YA}→{YB}  (red=fell, blue=rose; clipped ±{clim:.0f}%)",
                         "orientation": "vertical"})
    low = gp[gp["nhh_min"] < MIN_HH]
    if len(low):
        low.plot(ax=ax3, color="none", edgecolor="0.25", linewidth=0.2, hatch="////")
    ax3.set_title(f"Change in real income, {YA} → {YB}", fontsize=12)
    ax3.axis("off")
    ax3.text(0.5, -0.04, f"hatched = <{MIN_HH} sampled households (low precision) · "
             f"national mean +6.9%", transform=ax3.transAxes, ha="center", fontsize=8)

    fig.suptitle("Peru — real per-capita household income (constant 2025 soles, INEI methodology)",
                 fontsize=14, y=0.92)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"fig_income_levels_change_{YA}_{YB}.{ext}", dpi=160, bbox_inches="tight")
    print(f"Saved figures/fig_income_levels_change_{YA}_{YB}.pdf/.png  "
          f"(level scale S/{lvmin:.0f}-{lvmax:.0f}, change ±{clim:.0f}%)")


if __name__ == "__main__":
    main()
