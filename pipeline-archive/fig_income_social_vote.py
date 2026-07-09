"""Dos scatters departamentales estilo 'trust':
  (1) Índice de programas sociales (ENAHO M37 2025, nº programas/hogar) vs voto 2da vuelta.
  (2) Ingreso real per cápita vs voto 2da vuelta.   (el que faltaba)
Rojo = ganó izquierda, azul = ganó derecha (Keiko). Voto: INFOgob 2021 + ONPE 2026."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt, unicodedata, re
import figstyle as fs
from dataset_income import real_income
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"raw"; FIG=ROOT/"figures"/"03_elecciones"; FIG.mkdir(parents=True,exist_ok=True); DATA=ROOT/"datasets"
ONPE=Path("D:/Investigacion/LavaJato/data/raw/onpe/resultados")
INFOGOB=Path("D:/Investigacion/LavaJato/Base_de_datos_INFOgob (1)/PRESIDENCIAL 2021 - 2DA VUELTA/EG2021_2V_Resultados_Presidencial.xlsx")
def _n(s): return re.sub(r"\s+"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().upper().strip())
DEPTS={1:"AMAZONAS",2:"ANCASH",3:"APURIMAC",4:"AREQUIPA",5:"AYACUCHO",6:"CAJAMARCA",7:"CALLAO",8:"CUSCO",9:"HUANCAVELICA",10:"HUANUCO",11:"ICA",12:"JUNIN",13:"LA LIBERTAD",14:"LAMBAYEQUE",15:"LIMA",16:"LORETO",17:"MADRE DE DIOS",18:"MOQUEGUA",19:"PASCO",20:"PIURA",21:"PUNO",22:"SAN MARTIN",23:"TACNA",24:"TUMBES",25:"UCAYALI"}
N2C={_n(v):k for k,v in DEPTS.items()}; N2C["APURIMAC"]=3; N2C["JUNIN"]=12
def hhid(d): return d["conglome"].astype(str).str.zfill(6)+d["vivienda"].astype(str).str.zfill(3)+d["hogar"].astype(str).str.zfill(2)

# --- dept vote ---
def vote21():
    x=pd.read_excel(INFOGOB,sheet_name="Nivel_Distrital")
    org=[c for c in x.columns if x[c].astype(str).str.contains("FUERZA POPULAR").any()][0]
    vot=[c for c in x.columns if _n(c)=="VOTOS"][0]
    x=x[x[org].astype(str).str.contains("PERU LIBRE|FUERZA POPULAR",case=False)].copy()
    x["c"]=np.where(x[org].astype(str).str.contains("PERU LIBRE",case=False),"izq","der")
    x["dpto"]=x["Region"].map(lambda s:N2C.get(_n(s)))
    p=x.dropna(subset=["dpto"]).groupby(["dpto","c"])[vot].sum().unstack("c")
    return (100*p["izq"]/(p["izq"]+p["der"])).rename("castillo_pct")
def vote26():
    df=pd.read_csv(ONPE/"2026_2v"/"presidencial_2v_distrito.csv"); df.columns=[c.strip() for c in df.columns]
    j=[c for c in df.columns if "JUNTOS" in _n(c)][0]
    df["dpto"]=df["UBIGEO"].astype(str).str.zfill(6).str[:2].astype(int)
    p=df.groupby("dpto").agg(izq=(j,"sum"),der=("fuerza_popular","sum"))
    return (100*p["izq"]/(p["izq"]+p["der"])).rename("left_pct")

# --- dept income ---
def income_dept(yr):
    d=real_income(yr); d["dpto"]=d["ubigeo"].astype(str).str.zfill(6).str[:2].astype(int); d["pw"]=d["factor07"]*d["mieperho"]
    return d.groupby("dpto").apply(lambda g:np.average(g["ipcr_0"],weights=g["pw"]),include_groups=False).rename("income")

# --- dept social index (2025) ---
FOOD=["p701_01","p701_02","p701_03","p701_04","p701_05","p701_10"]
NONF=["p710_01","p710_02","p710_04","p710_05","p710_06","p710_07","p710_08","p710_10","p710_15","p710_28","p710_34","p710_29","p710_33"]
def social_dept():
    m=pd.read_stata(RAW/"programas_sociales"/"enaho-2025-37.dta",convert_categoricals=False); m.columns=[c.lower() for c in m.columns]
    cols=[c for c in FOOD+NONF if c in m.columns]
    m["nprog"]=sum((pd.to_numeric(m[c],errors="coerce")==1).astype(float) for c in cols)
    m["dpto"]=m["ubigeo"].astype(str).str.zfill(6).str[:2].astype(int)
    return m.groupby("dpto").apply(lambda g:np.average(g["nprog"],weights=g["factor07"]),include_groups=False).rename("social_idx")

# build panel
P=pd.DataFrame({"department":DEPTS}).reset_index().rename(columns={"index":"dpto"})
P=P.merge(vote21(),on="dpto").merge(vote26(),on="dpto").merge(income_dept(2021).rename("income21"),on="dpto").merge(income_dept(2025).rename("income25"),on="dpto").merge(social_dept(),on="dpto")
P.to_csv(DATA/"dept_income_social_vote.csv",index=False)

def panel(ax,x,y,won_left,xlab,ylab,ttl,labs):
    won=won_left
    ax.axhline(50,color=fs.GREY,ls=(0,(4,4)),lw=1)
    ax.scatter(x,y,s=46,c=np.where(won,fs.CRANBERRY,fs.NAVY),edgecolor="white",linewidth=1,zorder=5)
    sl,r,p=fs.ci_band(ax,x,y,color=fs.INK)
    fs.repel_labels(ax,x,y,[d.title() for d in labs],fs=7.5)
    ax.set_xlabel(xlab); ax.set_ylabel(ylab); ax.set_title(ttl,loc="left",color=fs.INK)
    ps="< 0.001" if p<0.001 else f"= {p:.3f}"
    fs.statbox(ax,[f"pendiente {sl:+.2f}",f"r = {r:+.2f}",f"p {ps}","n = 25 deptos"],loc="upper right" if r<0 else "upper left")

# FIGURE 1: social index vs vote
fs.use()
fig,(a1,a2)=plt.subplots(1,2,figsize=(14.5,7.2))
panel(a1,P["social_idx"].values,P["castillo_pct"].values,P["castillo_pct"].values>50,"Índice de programas sociales 2025 (nº prog./hogar)","% voto Castillo (izq)","2021",P["department"])
panel(a2,P["social_idx"].values,P["left_pct"].values,P["left_pct"].values>50,"Índice de programas sociales 2025 (nº prog./hogar)","% voto Juntos (izq)","2026",P["department"])
fig.suptitle("Programas sociales vs voto en 2da vuelta, por departamento",fontsize=14,fontweight="semibold",y=1.0)
fig.text(.5,.945,"Índice 2025 = nº promedio de programas por hogar (intensidad de la red social). Rojo=ganó izquierda, azul=Keiko.",ha="center",fontsize=9.5,color=fs.GREY)
fs.source(fig,"Fuente: ENAHO M37 (INEI) 2025; voto INFOgob 2021 + ONPE 2026.")
fig.tight_layout(rect=[0,0,1,0.93])
for e in("pdf","png"): fig.savefig(FIG/f"fig_social_vote_pro.{e}",dpi=180,bbox_inches="tight")

# FIGURE 2: income vs vote
fig,(a1,a2)=plt.subplots(1,2,figsize=(14.5,7.2))
panel(a1,P["income21"].values,P["castillo_pct"].values,P["castillo_pct"].values>50,"Ingreso real per cápita 2021 (S/mes)","% voto Castillo (izq)","2021",P["department"])
panel(a2,P["income25"].values,P["left_pct"].values,P["left_pct"].values>50,"Ingreso real per cápita 2025 (S/mes)","% voto Juntos (izq)","2026",P["department"])
fig.suptitle("Ingreso vs voto en 2da vuelta, por departamento",fontsize=14,fontweight="semibold",y=1.0)
fig.text(.5,.945,"¿Los departamentos más pobres votan más a la izquierda? Rojo=ganó izquierda, azul=Keiko.",ha="center",fontsize=9.5,color=fs.GREY)
fs.source(fig,"Fuente: ENAHO Sumaria (INEI) 2021/2025; voto INFOgob 2021 + ONPE 2026.")
fig.tight_layout(rect=[0,0,1,0.93])
for e in("pdf","png"): fig.savefig(FIG/f"fig_income_vote_pro.{e}",dpi=180,bbox_inches="tight")

from numpy import corrcoef as cc
print("Social idx vs Castillo21 r=%.2f | vs Juntos26 r=%.2f"%(cc(P.social_idx,P.castillo_pct)[0,1],cc(P.social_idx,P.left_pct)[0,1]))
print("Income21 vs Castillo21 r=%.2f | Income25 vs Juntos26 r=%.2f"%(cc(P.income21,P.castillo_pct)[0,1],cc(P.income25,P.left_pct)[0,1]))
print("OK -> fig_social_vote_pro.png, fig_income_vote_pro.png")
