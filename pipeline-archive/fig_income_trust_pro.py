"""#8 Income x trust binscatter (professional)."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import figstyle as fs
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/"figures"/"02_confianza"; FIG.mkdir(parents=True,exist_ok=True)
fs.use()
d=pd.read_csv(ROOT/"datasets"/"trust_income_2025.csv").dropna(subset=["income_pc","trust_share","factor07"])
x=d.income_pc.to_numpy(); y=d.trust_share.to_numpy()*100; w=d.factor07.to_numpy()
# 20 equal-weight bins
o=np.argsort(x); xs,ys,ws=x[o],y[o],w[o]; cw=np.cumsum(ws)/ws.sum()
cuts=np.searchsorted(cw,np.linspace(0,1,21)[1:-1])
bx=[np.average(a,weights=c) for a,c in zip(np.split(xs,cuts),np.split(ws,cuts))]
by=[np.average(a,weights=c) for a,c in zip(np.split(ys,cuts),np.split(ws,cuts))]
b1,b0=np.polyfit(x,y,1,w=w); r=np.cov(x,y,aweights=w)[0,1]/np.sqrt(np.cov(x,y,aweights=w)[0,0]*np.cov(x,y,aweights=w)[1,1])
fig,ax=plt.subplots(figsize=(9.5,6))
xx=np.linspace(min(bx),max(bx),50)
bb1,bb0=np.polyfit(bx,by,1)
ax.plot(xx,bb0+bb1*xx,color=fs.INK,lw=2,zorder=4)
ax.scatter(bx,by,s=70,color=fs.NAVY,edgecolor="white",lw=1.2,zorder=5)
ax.set_xlabel("Ingreso real per cápita, S/ por mes (soles 2025)")
ax.set_ylabel("Instituciones en las que confía (%)")
ax.set_ylim(min(by)-1.2,max(by)+1.0)
ax.text(0.5,-0.16,"Nota: el gradiente lo concentran los ventiles de mayor ingreso; entre hogares la correlación es casi nula (r=+0.03).",transform=ax.transAxes,ha="center",fontsize=8.5,color=fs.GREY)
fs.statbox(ax,[f"pendiente = {b1*1000:+.2f} pp / +S1000","r = "+f"{r:+.2f}","20 ventiles de ingreso (ponderados)","ENAHO 2025, n="+f"{len(d):,} hogares"],loc="upper left")
fig.suptitle("A mayor ingreso, algo más de confianza institucional — pero la relación es débil",
             fontsize=13.5,fontweight="semibold",y=1.0)
fs.source(fig,"Fuente: ENAHO Módulos 34 y 85 (INEI) 2025. Confianza = % de 21 instituciones con 'suficiente/bastante'.")
fig.tight_layout(rect=[0,0.05,1,0.97])
for e in("pdf","png"): fig.savefig(FIG/f"fig_income_trust_pro.{e}",dpi=200,bbox_inches="tight")
print("ok income-trust")
