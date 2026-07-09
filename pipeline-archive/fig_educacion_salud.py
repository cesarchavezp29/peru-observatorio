"""(1) Boom educativo por cohorte de nacimiento y sexo (M03 x M02, 2025).
   (2) Expansión del seguro de salud / SIS 2004-2025 (M04)."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
import figstyle as fs
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"raw"; FIG=ROOT/"figures"/"05_demografia_salud_educacion"; FIG.mkdir(parents=True,exist_ok=True); DATA=ROOT/"datasets"
def load(folder,m,yr):
    d=pd.read_stata(RAW/folder/f"enaho-{yr}-{m}.dta",convert_categoricals=False); d.columns=[c.lower() for c in d.columns]; return d
def pid(d): return d["conglome"].astype(str).str.zfill(6)+d["vivienda"].astype(str).str.zfill(3)+d["hogar"].astype(str).str.zfill(2)+d["codperso"].astype(str).str.zfill(2)
YRS={1:0,2:0,3:3,4:6,5:9,6:11,7:13,8:14,9:14,10:17,11:19,12:6}

# ===== (1) educación por cohorte =====
m3=load("educacion","03",2025); m2=load("miembros","02",2025)
m2["edad"]=pd.to_numeric(m2["p208a"],errors="coerce"); m2["sexo"]=pd.to_numeric(m2["p207"],errors="coerce")
m3["pid"]=pid(m3); m2["pid"]=pid(m2)
d=m3.merge(m2[["pid","edad","sexo","facpob07"]],on="pid",how="inner")
d["anios"]=pd.to_numeric(d["p301a"],errors="coerce").map(YRS)
d=d.dropna(subset=["anios","edad","sexo","facpob07"])
d=d[(d.edad>=25)&(d.edad<=74)]; d["cohorte"]=2025-d.edad
d["cbin"]=(d["cohorte"]//5)*5
def wm(g): return np.average(g["anios"],weights=g["facpob07"])
coh=d.groupby(["cbin","sexo"]).apply(wm,include_groups=False).unstack("sexo")

fs.use()
fig,(a1,a2)=plt.subplots(1,2,figsize=(13.5,6))
a1.plot(coh.index,coh[1],color=fs.NAVY,lw=2.4,marker="o",ms=4,label="Hombres")
a1.plot(coh.index,coh[2],color=fs.CRANBERRY,lw=2.4,marker="o",ms=4,label="Mujeres")
a1.set_xlabel("Año de nacimiento (cohorte)"); a1.set_ylabel("Años de educación promedio")
a1.set_title("(a) Boom educativo por cohorte",loc="left",fontsize=12); a1.grid(alpha=.25); a1.legend(fontsize=9)
a1.annotate("Las mujeres mayores\nestudiaron mucho menos",(coh.index[1],coh[2].iloc[1]),fontsize=8,color=fs.CRANBERRY,xytext=(8,-22),textcoords="offset points")
a1.annotate("...y las jóvenes\nya alcanzan a los hombres",(coh.index[-2],coh[2].iloc[-2]),fontsize=8,color=fs.CRANBERRY,xytext=(-90,8),textcoords="offset points")

# ===== (2) SIS / seguro de salud en el tiempo =====
rows=[]
for yr in range(2004,2026):
    s=load("salud","04",yr); f=pd.to_numeric(s["factor07"],errors="coerce")
    segv=[c for c in s.columns if c in [f"p419{i}" for i in range(1,9)]]
    anyseg=pd.concat([pd.to_numeric(s[c],errors="coerce")==1 for c in segv],axis=1).any(axis=1)
    sis=pd.to_numeric(s.get("p4195"),errors="coerce")==1; ess=pd.to_numeric(s.get("p4191"),errors="coerce")==1
    msk=f.notna()
    rows.append({"year":yr,"any":100*np.average(anyseg[msk],weights=f[msk]),"sis":100*np.average(sis[msk],weights=f[msk]),"essalud":100*np.average(ess[msk],weights=f[msk])})
S=pd.DataFrame(rows); S.to_csv(DATA/"sis_expansion.csv",index=False)
a2.plot(S.year,S["any"],color="#2f9e44",lw=2.6,marker="o",ms=3,label="Algún seguro de salud")
a2.plot(S.year,S["sis"],color=fs.CRANBERRY,lw=2.6,marker="o",ms=3,label="SIS (seguro público)")
a2.plot(S.year,S["essalud"],color=fs.NAVY,lw=2.6,marker="o",ms=3,label="EsSalud")
a2.set_xlabel("Año"); a2.set_ylabel("% de la población"); a2.set_title("(b) La explosión del SIS",loc="left",fontsize=12); a2.grid(alpha=.25); a2.legend(fontsize=9,loc="center right")
for yr in (2004,2025):
    r=S[S.year==yr].iloc[0]
    a2.annotate(f"{r['sis']:.0f}%",(yr,r['sis']),color=fs.CRANBERRY,fontsize=8.5,fontweight="semibold",xytext=(0,6),textcoords="offset points",ha="center")
    a2.annotate(f"{r['any']:.0f}%",(yr,r['any']),color="#2f9e44",fontsize=8.5,fontweight="semibold",xytext=(0,6),textcoords="offset points",ha="center")
fig.suptitle("Dos transformaciones del Perú: educación por cohorte y seguro de salud (ENAHO)",fontsize=14,fontweight="semibold",y=1.0)
fs.source(fig,"Fuente: ENAHO Módulos 03, 02, 04 (INEI). (a) 2025, adultos 25-74; (b) 2004-2025. Ponderado.")
fig.tight_layout(rect=[0,0,1,0.95])
for e in("pdf","png"): fig.savefig(FIG/f"fig_educacion_salud.{e}",dpi=140,bbox_inches="tight")
print("Educación por cohorte (años):"); print(coh.round(1).to_string())
print(f"\nSIS: {S['sis'].iloc[0]:.0f}% (2004) -> {S['sis'].iloc[-1]:.0f}% (2025) | Algún seguro: {S['any'].iloc[0]:.0f}% -> {S['any'].iloc[-1]:.0f}%")
print("OK -> fig_educacion_salud.png")
