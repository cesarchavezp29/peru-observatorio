"""Transición demográfica del Perú 2004-2025 (ENAHO M02, ponderado por factor07).
Pirámides poblacionales + tendencias de envejecimiento."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import figstyle as fs
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"raw"; FIG=ROOT/"figures"/"05_demografia_salud_educacion"; FIG.mkdir(parents=True,exist_ok=True); DATA=ROOT/"datasets"
YEARS=list(range(2004,2026))
def load(yr):
    d=pd.read_stata(RAW/"miembros"/f"enaho-{yr}-02.dta",convert_categoricals=False); d.columns=[c.lower() for c in d.columns]
    d["edad"]=pd.to_numeric(d["p208a"],errors="coerce"); d["sexo"]=pd.to_numeric(d["p207"],errors="coerce"); d["f"]=pd.to_numeric(d["facpob07"],errors="coerce")
    return d.dropna(subset=["edad","f"])

# tendencias
rows=[]
pyr={}
for yr in YEARS:
    d=load(yr); f=d["f"]; tot=f.sum()
    rows.append({"year":yr,"p_0_14":100*f[d.edad<15].sum()/tot,"p_15_64":100*f[(d.edad>=15)&(d.edad<65)].sum()/tot,
                 "p_65":100*f[d.edad>=65].sum()/tot,"p_60":100*f[d.edad>=60].sum()/tot,"edad_med":np.average(d.edad,weights=f)})
    if yr in (2004,2025):
        g=pd.cut(d.edad,bins=list(range(0,81,5))+[200],right=False,labels=[f"{i}" for i in range(0,81,5)])
        m=d[d.sexo==1].groupby(g,observed=False)["f"].sum()/tot*100
        w=d[d.sexo==2].groupby(g,observed=False)["f"].sum()/tot*100
        pyr[yr]=(m,w)
T=pd.DataFrame(rows); T["dep"]=100*(T.p_0_14+T.p_65)/T.p_15_64; T.to_csv(DATA/"demographic_transition.csv",index=False)
print(T[["year","p_0_14","p_65","edad_med","dep"]].round(1).to_string(index=False))

fs.use()
fig=plt.figure(figsize=(14,6.6)); gs=fig.add_gridspec(1,3,width_ratios=[1.1,1.1,1.4],wspace=.32)
# piramides
labels=[f"{i}-{i+4}" for i in range(0,80,5)]+["80+"]
for ax,yr in [(fig.add_subplot(gs[0,0]),2004),(fig.add_subplot(gs[0,1]),2025)]:
    m,w=pyr[yr]; yps=np.arange(len(labels))
    ax.barh(yps,-m.values,color=fs.NAVY,height=.82,label="Hombres"); ax.barh(yps,w.values,color=fs.CRANBERRY,height=.82,label="Mujeres")
    ax.set_yticks(yps[::2]); ax.set_yticklabels(labels[::2],fontsize=7.5); ax.set_title(f"Pirámide {yr}",loc="left",fontsize=11.5)
    ax.set_xlim(-6,6); ax.set_xticks([-4,-2,0,2,4]); ax.set_xticklabels(["4","2","0","2","4"],fontsize=8); ax.set_xlabel("% de la población")
    if yr==2004: ax.legend(fontsize=8,loc="upper left")
# tendencias
ax=fig.add_subplot(gs[0,2])
ax.plot(T.year,T.p_0_14,color=fs.GOLD,lw=2.2,marker="o",ms=3,label="Niños 0-14 (ENAHO)")
ax.plot(T.year,T.p_60,color=fs.CRANBERRY,lw=2.2,marker="o",ms=3,label="Adulto mayor 60+ (ENAHO)")
ax.plot(T.year,T.edad_med,color=fs.NAVY,lw=2.2,marker="o",ms=3,label="Edad mediana (ENAHO)")
# anclas oficiales Censo INEI (negro)
off={2017:{"k":26.5,"e":11.7,"m":29},2025:{"k":22.7,"e":14.8,"m":32}}
for yr,o in off.items():
    ax.scatter([yr,yr,yr],[o["k"],o["e"],o["m"]],color="black",s=42,zorder=8,marker="D")
ax.scatter([],[],color="black",marker="D",s=42,label="Censo INEI (oficial)")
ax.set_title("Envejecimiento (ENAHO vs Censo)",loc="left",fontsize=11.5); ax.set_xlabel("Año"); ax.grid(alpha=.25); ax.legend(fontsize=8,loc="center left")
fig.suptitle("La transición demográfica del Perú: ENAHO capta la tendencia; los niveles oficiales son del Censo",fontsize=14,fontweight="semibold",y=1.0)
fs.source(fig,"Fuente: ENAHO M02 (facpob07, línea) vs Censo INEI 2017/2025 (rombos). ENAHO sobre-estima ~3-4pp el adulto mayor y la población total.")
fig.tight_layout(rect=[0,0,1,0.95])
for e in("pdf","png"): fig.savefig(FIG/f"demographic_transition.{e}",dpi=125,bbox_inches="tight")
a,b=T.iloc[0],T.iloc[-1]
print(f"\nLOCO: niños 0-14 cayeron {a.p_0_14:.0f}%->{b.p_0_14:.0f}% | 65+ subieron {a.p_65:.0f}%->{b.p_65:.0f}% (x{b.p_65/a.p_65:.1f}) | edad mediana {a.edad_med:.0f}->{b.edad_med:.0f} años")
print("OK -> demographic_transition.png")
