"""#4 ¿Quién ganó cada distrito? 2da vuelta 2021 y 2026. ROJO=izquierda, AZUL=Keiko/derecha.
2021: INFOgob (JNE) resultado OFICIAL FINAL a nivel distrital (el scrape ONPE estaba al 95%
y perdia el VRAEM). 2026: ONPE resultadosegundavuelta. Cruce por nombres + crosswalk curado.
Gris = distritos creados en 2021 (votaron 1ra vez en 2022)."""
from pathlib import Path
import pandas as pd, numpy as np, geopandas as gpd, matplotlib.pyplot as plt
import unicodedata, re
from matplotlib.patches import Patch
import figstyle as fs
ROOT=Path(__file__).resolve().parents[1]; FIG=ROOT/"figures"/"03_elecciones"; FIG.mkdir(parents=True,exist_ok=True)
ONPE=Path("D:/Investigacion/LavaJato/data/raw/onpe/resultados")
INFOGOB=Path("D:/Investigacion/LavaJato/Base_de_datos_INFOgob (1)/PRESIDENCIAL 2021 - 2DA VUELTA/EG2021_2V_Resultados_Presidencial.xlsx")
SHP=Path("D:/Shining Path and Geographic/Final Results/Figures/Limite Distrital INEI 2025 CPV.shp")
def _n(s): return re.sub(r"\s+"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().upper().replace("-"," ").strip())
FIX={("ANCASH","HUARAZ","PAMPAS"):"PAMPAS GRANDE",("HUANUCO","HUANUCO","QUISQUI"):"QUISQUI (KICHKI)",
     ("TACNA","TARATA","CHUCATAMANI"):"HEROES ALBARRACIN",("CUSCO","LA CONVENCION","QUIMBIRI"):"KIMBIRI",
     ("JUNIN","CHUPACA","SAN JUAN DE YSCOS"):"SAN JUAN DE ISCOS",("HUANUCO","LEONCIO PRADO","DANIEL ALOMIAS ROBLES"):"DANIEL ALOMIA ROBLES",
     ("LIMA","HUAROCHIRI","LARAOS"):"SAN PEDRO DE LARAOS",("LIMA","YAUYOS","AYAUCA"):"ALLAUCA",
     ("APURIMAC","AYMARAES","HUAYLLO"):"IHUAYLLO",("AYACUCHO","VICTOR FAJARDO","HUAYA"):"HUALLA",
     ("CAJAMARCA","CONTUMAZA","SANTA CRUZ DE TOLEDO"):"SANTA CRUZ DE TOLED",("UCAYALI","ATALAYA","RAYMONDI"):"RAIMONDI",("AMAZONAS","RODRIGUEZ DE MENDOZA","MILPUCC"):"MILPUC",("PUNO","EL COLLAO","CAPASO"):"CAPAZO",
     ("AREQUIPA","AREQUIPA","SANTA RITA DE SIHUAS"):"SANTA RITA DE SIGUAS",
     ("AYACUCHO","PARINACOCHAS","SAN FRANCISCO DE RIVACAYCO"):"SAN FRANCISCO DE RAVACAYCO",
     ("HUANCAVELICA","ANGARAES","HUALLAY GRANDE"):"HUAYLLAY GRANDE"}
fs.use()
g=gpd.read_file(SHP)
for c in ("DEPARTAMEN","PROVINCIA","DISTRITO"): g[c+"_n"]=g[c].map(_n)
GKEY={(r.DEPARTAMEN_n,r.PROVINCIA_n,r.DISTRITO_n) for r in g.itertuples()}

def finalize(d):  # d has dep_n,prov_n,dist_n,izq,der
    d["prov_n"]=d["prov_n"].replace({"NAZCA":"NASCA","ANTONIO RAIMONDI":"ANTONIO RAYMONDI"}); d["dist_n"]=d["dist_n"].replace({"NAZCA":"NASCA"})
    d["dist_n"]=d.apply(lambda r:FIX.get((r["dep_n"],r["prov_n"],r["dist_n"]),r["dist_n"]),axis=1)
    d["tot"]=d["izq"]+d["der"]; d=d[d["tot"]>0].copy(); d["left"]=100*d["izq"]/d["tot"]
    inn=d.apply(lambda r:(r["dep_n"],r["prov_n"],r["dist_n"]) in GKEY,axis=1)
    cov=100*d[inn]["tot"].sum()/d["tot"].sum()
    return {(r["dep_n"],r["prov_n"],r["dist_n"]):r["left"] for _,r in d.iterrows()}, cov

def load_2021_infogob():
    x=pd.read_excel(INFOGOB,sheet_name="Nivel_Distrital")
    org=[c for c in x.columns if x[c].astype(str).str.contains("FUERZA POPULAR").any()][0]
    vot=[c for c in x.columns if _n(c)=="VOTOS"][0]
    x=x[x[org].astype(str).str.contains("PERU LIBRE|FUERZA POPULAR",case=False)].copy()
    x["cand"]=np.where(x[org].astype(str).str.contains("PERU LIBRE",case=False),"izq","der")
    x["dep_n"]=x["Region"].map(_n); x["prov_n"]=x["Provincia"].map(_n); x["dist_n"]=x["Distrito"].map(_n)
    d=x.pivot_table(index=["dep_n","prov_n","dist_n"],columns="cand",values=vot,aggfunc="sum").fillna(0).reset_index()
    return finalize(d)

def load_2026_onpe():
    df=pd.read_csv(ONPE/"2026_2v"/"presidencial_2v_distrito.csv"); df.columns=[c.strip() for c in df.columns]
    jc=[c for c in df.columns if "JUNTOS" in _n(c)][0]
    d=pd.DataFrame({"dep_n":df["departamento"].map(_n),"prov_n":df["provincia"].map(_n),
                    "dist_n":df["distrito"].map(_n),"izq":df[jc],"der":df["fuerza_popular"]})
    return finalize(d)

L21,c21=load_2021_infogob(); L26,c26=load_2026_onpe()
g["left21"]=[L21.get((r.DEPARTAMEN_n,r.PROVINCIA_n,r.DISTRITO_n),np.nan) for r in g.itertuples()]
g["left26"]=[L26.get((r.DEPARTAMEN_n,r.PROVINCIA_n,r.DISTRITO_n),np.nan) for r in g.itertuples()]

fig,(a1,a2)=plt.subplots(1,2,figsize=(13,8.6))
for ax,col,ttl in [(a1,"left21","2021  ·  Castillo (Perú Libre) vs Keiko"),
                   (a2,"left26","2026  ·  Juntos por el Perú vs Keiko (empate técnico)")]:
    c=np.where(g[col].isna(),"#d9d9d9",np.where(g[col]>50,fs.CRANBERRY,fs.NAVY))
    g.plot(ax=ax,color=c,edgecolor="white",linewidth=0.06); ax.set_title(ttl,loc="left",fontsize=12,color=fs.INK); ax.axis("off")
    ax.text(0.5,-0.02,f"{int(g[col].notna().sum()):,} distritos",transform=ax.transAxes,ha="center",fontsize=8,color=fs.GREY)
leg=[Patch(fc=fs.CRANBERRY,ec="white",label="Ganó la izquierda (Perú Libre / Juntos)"),
     Patch(fc=fs.NAVY,ec="white",label="Ganó Keiko / derecha"),
     Patch(fc="#d9d9d9",ec="white",label="Distrito creado en 2021 (votó 1ra vez en 2022)")]
fig.legend(handles=leg,loc="lower center",ncol=3,bbox_to_anchor=(0.5,0.05),fontsize=9.5)
fig.suptitle("¿Quién ganó cada distrito en segunda vuelta?",fontsize=14,fontweight="semibold",y=0.96)
fs.source(fig,f"Fuente: 2021 INFOgob/JNE (oficial final); 2026 ONPE (resultadosegundavuelta.onpe.gob.pe). Cobertura: 2021 {c21:.1f}%, 2026 {c26:.1f}%. Mapa INEI 2025.")
g[["UBIGEO","DEPARTAMEN","PROVINCIA","DISTRITO","left21","left26"]].to_csv(ROOT/"datasets"/"district_vote_2021_2026.csv",index=False)
for e in("pdf","png"): fig.savefig(FIG/f"fig_electoral_map.{e}",dpi=190,bbox_inches="tight")
print(f"2021: {int(g['left21'].notna().sum())} distritos coloreados, {int(g['left21'].isna().sum())} grises, cob {c21:.2f}%")
print(f"2026: {int(g['left26'].notna().sum())} distritos coloreados, {int(g['left26'].isna().sum())} grises, cob {c26:.2f}%")
