"""Focalización de programas sociales (ENAHO M37 2025): cobertura por decil de ingreso.
Merge M37 (hogar) x Sumaria/ingreso (hogar) 1:1. Pro-pobre = la cobertura cae con el ingreso."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import figstyle as fs
from dataset_income import real_income
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"raw"; FIG=ROOT/"figures"/"04_programas_sociales"; FIG.mkdir(parents=True,exist_ok=True); DATA=ROOT/"datasets"
YEAR=2025
PROG={"Juntos":"p710_04","Pensión 65":"p710_05","Qali Warma (desayuno escolar)":"p701_03",
      "Vaso de Leche":"p701_01","Comedor popular":"p701_02","Bono Gas (FISE)":"p710_15"}
def hhid(d): return d["conglome"].astype(str).str.zfill(6)+d["vivienda"].astype(str).str.zfill(3)+d["hogar"].astype(str).str.zfill(2)

m=pd.read_stata(RAW/"programas_sociales"/f"enaho-{YEAR}-37.dta",convert_categoricals=False); m.columns=[c.lower() for c in m.columns]
m["hhid"]=hhid(m)
for lab,v in PROG.items(): m[lab]=(pd.to_numeric(m[v],errors="coerce")==1).astype(float)
inc=real_income(YEAR); inc["hhid"]=hhid(inc)
d=m.merge(inc[["hhid","ipcr_0","mieperho"]],on="hhid",how="left").dropna(subset=["ipcr_0","factor07"])
print(f"merge M37 x ingreso: {len(m):,} hogares -> {d['ipcr_0'].notna().sum():,} con ingreso (1:1)")
# deciles ponderados por persona
d=d.sort_values("ipcr_0"); pw=d["factor07"]*d["mieperho"]; cw=np.cumsum(pw)/pw.sum()
d["decil"]=np.searchsorted(np.linspace(0,1,11)[1:-1],cw)+1
# cobertura nacional + por decil (ponderada por factor07)
print("\nCobertura nacional ponderada:")
nat={}
for lab in PROG: nat[lab]=100*np.average(d[lab],weights=d["factor07"]); print(f"  {lab}: {nat[lab]:.1f}%")
cov=d.groupby("decil").apply(lambda g:pd.Series({lab:100*np.average(g[lab],weights=g["factor07"]) for lab in PROG}),include_groups=False)
cov.to_csv(DATA/f"social_coverage_by_decile_{YEAR}.csv")

fs.use()
fig,ax=plt.subplots(figsize=(11,6.4))
pal=[fs.CRANBERRY,fs.NAVY,fs.GOLD,"#2f9e44","#7b2cbf","#8a8f98"]
for (lab,_),col in zip(PROG.items(),pal):
    ax.plot(cov.index,cov[lab],marker="o",ms=6,lw=2,color=col,label=f"{lab} ({nat[lab]:.0f}%)")
ax.set_xticks(range(1,11)); ax.set_xlabel("Decil de ingreso real per cápita (1 = más pobre, 10 = más rico)")
ax.set_ylabel("% de hogares que recibe el programa"); ax.set_xlim(.7,10.3); ax.grid(alpha=.25)
ax.legend(title="Programa (cobertura nacional)",fontsize=9,title_fontsize=9.5,loc="upper right")
fig.suptitle("Focalización de programas sociales por decil de ingreso, 2025",fontsize=14,fontweight="semibold",y=1.0)
fig.text(.5,.945,"Pendiente negativa = pro-pobre (llega más a los hogares de menor ingreso)",ha="center",fontsize=10,color=fs.GREY)
fs.source(fig,"Fuente: ENAHO Módulo 37 (Programas Sociales) x Sumaria, INEI 2025. Ponderado por factor07.")
fig.tight_layout(rect=[0,0,1,0.94])
for e in("pdf","png"): fig.savefig(FIG/f"fig_social_targeting_{YEAR}.{e}",dpi=180,bbox_inches="tight")
print("\nOK -> figures/fig_social_targeting_2025.png")
