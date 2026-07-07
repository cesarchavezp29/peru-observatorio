# ENDES toolkit (Encuesta Demográfica y de Salud Familiar)

Peru's DHS (Demographic and Health Survey), built as the **third INEI survey track** in
this repo alongside the ENAHO cross-section (`README.md`) and the ENAHO Panel
(`docs/NOTES_panel.md`). ENDES is the right survey for fertility, maternal/child health,
domestic violence, contraception, and — with its month-level birth calendar and parity —
the proper home for child-penalty / fertility-timing work that ENAHO can only approximate.

Everything below was verified live against the INEI server on **2026-06-20**. Single
sources of truth in code: `scripts/endes_codes.py` (year→code + discovery),
`scripts/endes_download.py` (downloader), `scripts/clean_endes_women.py` (first cleaner).
Companion deep-notes: `docs/NOTES_endes.md`.

---

## 1. THE KEY GOTCHA — ENDES is served in SPSS, not STATA

ENAHO downloads as `…/descarga/STATA/{CODE}-Modulo{NN}.zip`. **For ENDES the STATA
segment exists only for 2020+ releases.** Every older year (1996, 2000, 2004–2019)
returns **404 under `/STATA/` but 200 under `/SPSS/`** (and `/DBF/`). SPSS is the only
format available for *every* ENDES year, so the toolkit standardizes on it:

```
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/SPSS/{CODE}-Modulo{NN}.zip
```

Files are `.sav`, read with `pyreadstat.read_sav`. (Diagnosed after a STATA-only probe
found 0 modules for every pre-2020 year and looked like the codes were wrong — the codes
were right, the format was the problem. INEI offers SPSS/CSV/STATA/DBF in general but
coverage by format×year is uneven: ENDES 2010 = STATA 404, **SPSS 200**, CSV 404, DBF 200.)

## 2. Year → proyecto code (`endes_codes.ENDES_CODE`)

One code per year (no quarterly split, unlike ENAHO). All 2004–2024 confirmed
SPSS-reachable live:

| year | code | year | code | year | code | year | code |
|--|--|--|--|--|--|--|--|
| 1996 | 32 | 2007 | 194 | 2014 | 441 | 2021 | 760 |
| 2000 | 35 | 2008 | 209 | 2015 | 504 | 2022 | 786 |
| 2004 | 120 | 2009 | 238 | 2016 | 548 | 2023 | 910 |
| 2005 | 150 | 2010 | 260 | 2017 | 605 | 2024 | 968 |
| 2006 | 183 | 2011 | 290 | 2018 | 638 | | |
| 2007 | 194 | 2012 | 323 | 2019 | 691 | | |
| | | 2013 | 407 | 2020 | 739 | | |

Source: INEI catalogue `codigosencuesta.rds`. Verify a new code's content before trusting it.

## 3. Module numbers shift by era (INEI `modulosdata.rds`)

ENDES module numbers are **not stable across years** (same trap as the panel's 01→1474).
`endes_download.modules_for(year)` returns the right set:

* **1996–2019 — DHS recode modules 64–74 (NO 68):**
  64 Hogar · 65 Vivienda · 66 Datos Básicos de MEF · 67 Historia de Nacimientos + Conoc.
  de Métodos · 69 Embarazo/Parto/Puerperio/Lactancia · 70 Inmunización y Salud ·
  71 Nupcialidad/Fecundidad/Cónyuge y Mujer · 72 Conoc. de SIDA/uso del condón ·
  73 Mortalidad Materna/Violencia Familiar · 74 Peso y talla/Anemia (1996, 2005+).
  Plus **413** Disciplina Infantil & **414** Encuesta de Salud (from 2013), **569**
  Programas Sociales (from 2014).
* **2020–2024 — contiguous block 1629–1641** (same content renumbered).

## 4. Each module zip ships SEVERAL DHS recode `.sav` files

Unlike ENAHO (one `.dta`/module), an ENDES module zip contains the DHS **recode**
subfiles — the real analysis units. Recode dictionary (verified 2004–2006):

| recode | unit (rows) | key | contents |
|--|--|--|--|
| **RECH0** | household | `hhid` | household record, `hv005` weight, `hv024` region, `hv025` urban/rural |
| **RECH1** | hh member | `hhid+hvidx` | `hv101` parentesco, `hv104` sexo, `hv105` edad, `hv106` educación |
| **RECH2/RECH23** | household | `hhid` | servicios de la vivienda (agua/luz/…) |
| **RECH4** | hh member | `hhid+idxh4` | salud/seguro de miembros (vars SH*) |
| **RECH5** | woman | `hhid` | antropometría de la mujer (HA*) |
| **RECH6** | child | `hhid` | antropometría del niño (HC*) |
| **REC0111** | woman 15-49 | `caseid` | IR core: `v005` peso, `v012` edad, `v013` grupo, `v106` educ nivel, `v133` educ años, `v024` región, `v025` área, `v190` riqueza |
| **REC2231x** | woman | `caseid` | reproducción: `v201` hijos nacidos vivos (CEB), `v213` embarazada, `v212` edad 1er nacimiento, `v208` nac. últ. 5 años |
| **REC21** | birth | `caseid+bidx` | historia de nacimientos (BR): `b0`-`b11` fechas/supervivencia |
| **REC41** | birth | `caseid+midx` | embarazo/parto/lactancia por nacimiento (M*) |
| **REC42** | woman | `caseid` | anticoncepción (`v401`+) |
| **REC43** | child | `caseid+hidx` | salud/inmunización del niño (H*) |
| **REC44** | child | `caseid+hwidx` | antropometría del niño (HW*) |
| **REC5161x** | woman | `caseid` | nupcialidad/fecundidad: `v501` estado civil, `v511` edad 1ª unión |
| **REC75/81** | woman | `caseid` | trabajo/empoderamiento/violencia (V750+) |
| **REC82** | woman×mes | `caseid` | **calendario reproductivo** (`vcal`/`vcol`) — clave para timing mensual |
| **REC83** | sibling | `caseid+mmidx` | historia de hermanas / mortalidad materna (MM*) |
| **REC84_DV** | woman | `caseid` | módulo de violencia doméstica (MMC*) |
| **REC91** | woman | `caseid` | vars INEI: `v190` riqueza, `sdepart/sregion/sprovin/sdistri` geografía, `sweight` |
| **REC94/REC95** | child | `caseid+idx` | módulos INEI adicionales de salud infantil |

**DHS weights:** `hv005` (household) and `v005` (women) are integers ×1,000,000 →
**divide by 1e6** before weighting. `caseid` case varies across years (`caseid`/`CASEID`)
— always lowercase columns on read.

## 5. Pipeline / scripts

| script | role |
|--|--|
| `endes_codes.py` | year→code map (`ENDES_CODE`) + `discover()` HEAD-probe; default format SPSS |
| `endes_download.py` | download ALL years (default 2004-2024) in SPSS; extract + verify every `.sav`; manifest `raw/endes/_endes_manifest.csv` |
| `clean_endes_women.py` | **first cleaner** — harmonized women's (MEF 15-49) dataset, merging REC0111+REC2231x+REC5161x+REC91 on `caseid` → `datasets/endes_mujeres_<from>_<to>.csv` |

Raw lands in `raw/endes/<year>_<code>/<INEI_subfolder>/<RECODE>.sav` (gitignored).
**Always `cd scripts` first** (or `PYTHONPATH=…/scripts`) — cwd resets to home between
shells and the sibling imports need it; run with `py -3.14`.

```
py -3.14 endes_download.py --from 2004 --to 2024      # download (SPSS)
py -3.14 clean_endes_women.py --from 2004 --to 2006   # clean women's file
```

## 6. Datasets produced

* **`datasets/endes_mujeres_2004_2024.csv`** (+`.parquet`) — 566,573 women 15-49,
  21 years stacked (restricted to MEF 15-49; see §6b).
  **Plus** `datasets/endes_miembros_2004_2024.csv` (2.46M household members, RECH1+RECH0
  wealth) and `datasets/endes_nacimientos_2004_2024.csv` (1.15M births, REC21/BR with
  CMC dates + mother age-at-birth). Columns: `anio, codigo, caseid, wt` (=v005/1e6), `edad, grupo_edad,
  educ_nivel, educ_anios, area, depto, region_dhs, riqueza, estado_civil, hijos_nacidos
  (CEB), embarazada, edad_primer_hijo, edad_primera_union, nac_ult5`, + raw id vars.
  100% weighted. **Validation:** weighted children-ever-born rises 1.91 (2004) → 1.94
  (2005) → 1.96 (2006), mean age ~30 — consistent with Peru DHS reports for the period.

## 6b. Comparability breaks — track BEFORE any series (verified 2026-06-20)

Same discipline as ENAHO's `INCONSISTENCIES.md`. Two confirmed breaks:

* **MEF universe expanded to adolescents 12-14 from 2018.** Pre-2018 the women's
  recode (REC0111) covers 15-49; **2018+ covers 12-49** (~12% rising to ~17% of rows are
  <15). Left unfiltered this breaks CEB, mean age, education and composition at 2018.
  `clean_endes_women.py` **restricts to MEF 15-49** for a comparable panel (the 12-14
  extension stays in raw if ever needed). This was a real cleaning bug, now fixed.
* **The 2017→2018 fertility "step" is a REAL decline, validated vs official INEI.**
  Cross-checked against INEI *Series anuales ENDES 1986-2024*, Cuadro 3.1 (national TGF):
  official 2.5 (2016) → 2.4 (2016-17) → 2.2 (2017-18) → 2.0 (2018-19) → 1.9 (2020) → 1.8
  (2024). Our births-based ASFR reproduces this within ~0.05-0.10 every year (2009
  2.57/2.6, 2014 2.45/2.5, 2020 1.91/1.9, 2022 1.91/1.9, 2023 1.81/1.8, 2024 1.73/1.8;
  small downward bias recent years from the exposure approximation). The apparent sharp
  2017→2018 step is a PRESENTATION effect: INEI publishes overlapping 3-year moving
  windows (which smooth), we plot single years. The underlying 0.5-0.6-child drop over
  2016-2020 is genuine, not a merge/redesign artifact. (INEI also notes "muestreo
  equilibrado 2015-2024".) NB ENAHO cannot compute TGF — no birth history; TGF is
  ENDES/Census only.

* **2004-2008 files are CUMULATIVE, not annual (verified 2026-06-21 via v008).** The
  early "annual" codes nest prior years: code 183 (2006) = interviews 2003-2006, code 194
  (2007) = 2003-2007, etc.; only 2009+ are clean single-year. Plotting them as separate
  years gives spurious "jumps" (each point is a running pooled average over largely the
  SAME interviews — e.g. a fake 2006->2007 move). FIX: `scripts/endes_units.py` assigns
  every record to its TRUE calendar year via `v008`/`hv008` and takes each year from ONE
  source (2004-2007 from code 194, 2008 from code 209, 2009+ annual). All cleaners and
  figure builders import it (`eu.dir_for(y)` + `eu.true_year_mask`). After the fix the
  series are smooth and the early period is true-annual (smaller n, honest sampling
  variation — INEI itself pools 2004-2006 & 2007-2008 for this reason).

## 6c. Indicators & figures

* **`datasets/endes_indicadores.csv`** — national per-year (2004-2024), weighted &
  ballpark-validated vs INEI/DHS: `tfr` (ASFR, 36-mo window), `adol_madre` (% 15-19
  madre/embarazada), `educ_anios`, `superior_pct`, `edad_1er_hijo`, `desnutricion`
  (stunting <5, hw70<-2DE), `anticon_mod` (modern contraception — only resolves in some
  years; the method var name drifts, pending). Built by `build_endes_indicators.py`.
* **Figures (`figures/14_endes/`, figstyle, ENDES-only source, NO boxed annotations —
  takeaway in the footnote):**
  - `fig_endes_series.py`: `fig_endes_tfr` (TGF 2.4→1.7, crosses replacement ~2018),
    `fig_endes_adol_madre` (adolescent motherhood 12.7%→8.2%), `fig_endes_desnutricion`
    (chronic malnutrition 29%→12%, flagship), `fig_endes_educacion` (schooling 9.5→11.1 yr).
  - `fig_endes_salud.py`: `fig_endes_mortalidad` (IMR 46→13 & U5MR 61→14 by birth cohort,
    censored cohorts dropped), `fig_endes_desnut_riqueza` (stunting by wealth quintile —
    27.7% poorest vs 3.4% richest, 8× gradient), `fig_endes_anticoncepcion` (modern
    contraception 30%→41%).
  - `fig_endes_geo.py`: `fig_endes_mapa_adolescente` (department choropleth — Amazonia
    ~21% vs south coast ~5%), `fig_endes_corr_educ_adol` (education↔teen-motherhood by
    department, r=−0.66). Uses v024 department labels matched to the INEI 2025 shapefile.
  - `fig_endes_violencia_anemia.py`: `fig_endes_violencia` (violence by partner — physical
    d106|d107 41%→26%, emotional d104, sexual d108; NB INEI's broader "psicológica/verbal"
    incl. controlling behaviours runs ~50%), `fig_endes_anemia` (child anemia 6-35 mo hc57,
    59%→~40% — the "agenda pendiente" contrasting the stunting success; hemoglobin
    altitude-adjustment breaks early-period comparability).
  - `fig_endes_materna.py`: `fig_endes_parto_institucional` (institutional delivery,
    national+urban/rural — rural 46%→81%), `fig_endes_cesarea` (17%→38%, above WHO range),
    `fig_endes_prenatal` (4+ antenatal visits).
  - `fig_endes_infancia.py`: `fig_endes_infancia` (diarrhea 15%→12% & fever in last 2 wks,
    children <5; h11 codes 1=24h/2=2wk).
  - `fig_endes_infancia2.py`: `fig_endes_vacunas` (basic complete immunization 12-23 mo —
    BCG+3DPT+3polio+measles h2-h9, ~57%→75%, age from REC21 CMC) and `fig_endes_lme`
    (exclusive breastfeeding <6 mo, v404 + 24h recall v409-v414 minus v411 expressed milk,
    stable ~68% — among the region's highest; validated vs INEI).
  - `fig_endes_mapas.py`: department choropleths `fig_endes_mapa_anemia` (Puno 72% — the
    altitude story), `fig_endes_mapa_desnutricion` (Huancavelica 30%), `fig_endes_mapa_parto`.
  - `fig_endes_correlaciones.py`: `fig_endes_corr_heatmap` (dept-indicator correlation
    matrix — education is the master variable, anemia the divergent one), plus scatters
    `fig_endes_corr_desnut_educ` (r=−0.88) and `fig_endes_corr_anemia_des` (r=0.50).
    Dept table cached to `datasets/endes_dept_indicadores.csv`.
  - `fig_endes_mujer.py`: `fig_endes_mort_materna` (PMDF — maternal deaths as % of female
    15-49 deaths, 23%→8% by death period, from sibling histories REC83/mm9; the per-100k
    ratio needs the full sisterhood exposure model, not computed), `fig_endes_empoderamiento`
    (decides own health v743a 74%→92%, rejects all wife-beating justifications v744a-e →99%).
  - `fig_endes_vih.py`: `fig_endes_vih` (HIV knowledge — heard of AIDS 91%→98%, condom
    prevents 76%→83%, one-partner prevents ~87%).
  - `fig_endes_mapas2.py`: `fig_endes_mapa_cesarea` (Tumbes/Lima ~47%), `fig_endes_mapa_violencia`
    (physical partner violence — Apurimac 41%, sierra sur highest).
  - `fig_endes_cohortes.py`: `fig_endes_cohortes` (synthetic-cohort CEB-by-age schedules —
    each younger birth cohort below the older at every age; the fertility transition).
  - `fig_endes_gradientes.py`: social-gradient cross-tabs (pooled 2016-2024) —
    `fig_endes_grad_adol_riqueza` (teen motherhood 20%→3% poorest→richest, 7x),
    `fig_endes_grad_cesarea_riqueza` (cesarean 15%→61%, "de ricas"),
    `fig_endes_grad_parto_riqueza` (only poorest quintile lags), `fig_endes_grad_violencia_educ`
    (physical violence ~31% for none/primary/secondary, 24% for higher ed).
  - `fig_endes_cesarea_sector.py`: `fig_endes_cesarea_sector` (cesarean by place-of-delivery
    sector — MINSA 29%, EsSalud 44%, FF.AA./PNP 57%, **private 77%**; isolates the private
    over-medicalization, >5x the WHO 10-15% band). Validated: national 38.2% = INEI Cuadro
    pág. 88; urban 44%/rural 21% official consistent with the wealth gradient.
  - `fig_endes_cruces.py`: more cross-correlations — `fig_endes_cruce_edad1_educ` (age at
    1st birth 19→24 yr by education), `fig_endes_cruce_anticon_riqueza` (modern contraception
    34%→39%), `fig_endes_cruce_anemia_riqueza` (child anemia 53%→27% poorest→richest, but
    27% even among rich = altitude/diet), `fig_endes_cruce_cesarea_tiempo` (MINSA vs private
    cesarean over time, persistent gap), `fig_endes_cruce_violencia_auto` (physical violence
    24% if woman decides own health vs 40% if not — correlational, bidirectional).
  - **Contraception deep-dive** (`fig_endes_anticon_composicion.py`, `fig_endes_anticon_metodos.py`,
    `fig_endes_metodos_individual.py`): modern‑method use is NON‑monotonic in wealth because
    TOTAL use is flat (~50%) but the MIX shifts — poorest rely on the **injectable** (16%→7%)
    and **traditional** (rhythm/withdrawal), richest use **condom** (4.5%→13.8%, 3×), **IUD**
    (0.3%→2.7%, 9×) and sterilization. One chart per method (v312) by wealth quintile.
    **Validated vs INEI**: official ENDES states injectable is highest in the lowest wealth
    quintile (24% among women in union); condom/IUD concentrated in urban/educated/wealthy.
    NB our levels are among ALL MEF 15‑49 (INEI reports among women in union = higher levels,
    same gradient). Reminder: condom = MODERN (barrier); rhythm/withdrawal = traditional.
  - **In-union version** (`fig_endes_anticon_unidas.py`, ADDED alongside, not replacing):
    same analysis among women in union (v502==1) to match INEI's universe — `*_unidas`
    figures. **Near-exact validation**: injectable in the poorest quintile = **25.0%** vs
    INEI official **24%**; condom rises 6%→19%, rhythm 17%→9%. Confirms the universe was the
    only difference between our all-MEF figures and INEI's published levels.
  ~29 figures over modules: MEF/women, birth history, anthropometry, contraception,
  household wealth, maternal health, child health, domestic violence, sibling histories,
  HIV — all validated vs INEI (TGF vs official Cuadro 3.1 within ~0.1; anemia 6-35 mo vs
  Cuadro 10.14.3 within ~0.2; vaccination, exclusive breastfeeding, institutional delivery,
  cesarean section all matched to INEI ballpark).

## 7. Status & next steps

* **Download: COMPLETE (2026-06-20).** 2004–2024 in SPSS — **593/594 recodes OK, 21
  years, 2.71 GB** (`raw/endes/_endes_manifest.csv`, one row per recode with rows/cols/
  status). Module counts: 10/yr (2004–2012), 12 (2013), 13 (2014–2024). The single
  non-OK is `2004 Modulo74` (peso/talla/anemia) = 404 — an INEI **source gap** (module 74
  starts 2005 per the catalogue), not a pipeline failure. Every `.sav` was verified by
  opening it (rows>0), not by byte count.
* **Cleaning:** women's file 2004–2006 done. NEXT — extend the women's cleaner to all
  years; build a **household members** file (RECH1) and a **births** file (REC21/BR, with
  CMC dates) for fertility + month-precise child-penalty analysis; harmonize the INEI
  geography (`sdepart/sprovin`) into a stable ubigeo; validate fertility/health
  indicators vs published INEI/DHS reports before any figure (same gate discipline as
  ENAHO).
