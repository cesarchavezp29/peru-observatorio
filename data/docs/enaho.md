# Mastering ENAHO

A clean, reproducible toolkit for Peru's **Encuesta Nacional de Hogares (ENAHO)** —
the official INEI household survey used to measure income, poverty, employment,
education, health and governance.

The goal: go from **raw INEI microdata → clean harmonized data → purpose-built
analysis datasets → official-statistic reproductions, maps and charts**, with
every step scripted and re-runnable, and the data auto-updating when INEI
publishes a new year.

---

## Pipeline layers

```
  INEI server
      │   scripts/download_enaho.py        (full pull + --update incremental)
      ▼
  raw/        one .dta per (year, module), standardized names, verified on download
      │   scripts/build_clean.py           (harmonize ids, types, labels across years)
      ▼
  clean/      one tidy file per (year, module) + a pooled long panel
      │   scripts/dataset_*.py             (one builder per research purpose)
      ▼
  datasets/   analysis-ready CSV/parquet  (income, trust, poverty, employment, ...)
      │   scripts/fig_*.py
      ▼
  figures/    maps & charts
```

| Folder      | Contents |
|-------------|----------|
| `raw/`      | Exactly what INEI ships, just renamed `enaho-<year>-<module>.dta`. Never edited. |
| `clean/`    | Harmonized: consistent ids, string/numeric types reconciled across years. |
| `datasets/` | Purpose-built, documented, reproducible analysis tables. |
| `figures/`  | Output maps and charts. |
| `docs/`     | Data dictionaries and the **variable/question change tracker**. |
| `scripts/`  | All code. `enaho_codes.py` is the single source of truth for INEI codes. |

---

## The data: INEI download codes

INEI serves each survey-year as a numbered *proyecto*:

```
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/{CODE}-Modulo{NN}.zip
```

`CODE` is a global project id, **not** the year. The full map (2004→2025) lives in
`scripts/enaho_codes.py`, verified against the local INEI archive and live HEAD
requests. **2025 = code 1031** (published May 2026; national poverty 25.7%).

---

## ENAHO Panel (longitudinal) — separate toolkit

The annual survey is a repeated cross-section (new households each year). INEI
also runs the **ENAHO Panel**, which re-interviews a *fixed* set of households
across consecutive years — the raw material for true poverty dynamics,
transitions and within-person fixed effects (vs the synthetic pseudo-panels the
cross-section forces). It is a **separate set of proyecto codes** and uses a
**different module numbering**. Full detail in [`docs/NOTES_panel.md`](docs/NOTES_panel.md)
and the auto-generated [`docs/PANEL_STRUCTURE.md`](docs/PANEL_STRUCTURE.md); single
source of truth `scripts/panel_codes.py`.

Release year → code: 2011→302, 2015→529, 2016→614, 2017→612, 2018→651,
2019→699, 2020→743, 2021→763, 2022→845, 2023→912. Each release is an
**overlapping 5-year balanced panel** (2007–11, 2011–15, 2012–16, …), independently
weighted — *do not* assume ids are comparable across releases.

Two module schemes (the trap): old releases (≤2017) use zero-padded
`01/03/04/05/34` (+`1314` miembros); new releases (≥2018) use the `1474–1479`
block. Files are **WIDE** (one row per household, columns suffixed `_NN` by year);
`scripts/panel_io.load_long()` reshapes to a tidy long panel. Keys: household
`cong+vivi+num_hog`, person `cong+vivi+p201p`. Always restrict to a balanced
window via the `hpan<window>`/`perpanel<window>` flag and weight with
`fac_panel<window>`.

```
py -3.14 panel_download.py                 # all releases × era-modules
py -3.14 inspect_panel.py                  # metadata structure map
py -3.14 panel_pobreza_dinamica.py raw/panel/2011_302/sumaria_2007_2011_panel.dta --label 2007-2011
```

Flagship result (2007–11, n=1,129 hh): the static 34% poverty rate hides that
only **14.5% are chronically poor** while **42.5% churn in and out** — poverty is
rotational, not a fixed third. Figures in `figures/13_panel/`.

**Frame vs panel (the row count is deceptive):** the long dataset is ~1.62M
household-wave rows across 10 releases, which looks cross-section-sized — but ENAHO
is a *rotating* panel, so each release's 5-year frame is ~87k–133k households while
only **~1–2k per release are balanced** (all 5 waves, `in_balanced==1`). The frame
is kept so the full sample reproduces official marginals (`w_xsec`); all dynamics
filter to `in_balanced==1` × `w_panel`. See `docs/NOTES_panel.md` §6.

### ⚠️ Panel weights: use the RIGHT weight for the question (and a process lesson)

The panel sumaria ships **two kinds of weight**, and using the wrong one fabricates
a fake discrepancy:

| weight | what it is | use it for |
|--|--|--|
| `fac_NN` / `factor07_NN` (per wave) | **cross-sectional** expansion weight for everyone interviewed in wave `NN` | reproducing an **annual marginal** (poverty/income for one year) |
| `fac_panel<window>` / `perpanel<window>` | **longitudinal** weight for the balanced survivors of that window | **dynamics** (chronic/transient, transitions, FE) |

`panel_validate.py` confirms the **full sample × per-wave cross-sectional weight
reproduces official INEI poverty to 0.00pp across all 20 downloaded waves** — the
panel microdata is sound. The balanced survivors weighted longitudinally deviate
by ±several pp (sign varies by release): that is **survivor composition**, a
diagnostic, *not* a data error. See `figures/13_panel/fig_panel_validation_pobreza`.

**Process lesson (this is the thing to avoid):** an earlier pass weighted the
balanced subsample with the longitudinal weight to reproduce an *annual* number,
saw a ~2.6pp gap, and was about to write it off as *"expected drift."* It was not
expected — it was the wrong weight on the wrong sample. **When a validation number
is off, investigate the method (weight, sample, universe) before labeling the gap
"expected."** A discrepancy you can't explain is a finding, not a footnote. Same
discipline as "numbers match the logs" and the cross-section comparability checks.

---

## How ENAHO is built: module granularity & merge keys

ENAHO is not one table — it is **29 modules** (for 2025), each a separate `.dta`
with its **own row granularity and its own universe**. Merging them safely is the
whole game. The merge key is whatever set of identifiers makes a row unique; we
read it **empirically from the data**, not from documentation:

```bash
python inspect_modules.py            # → docs/MODULE_MERGE_KEYS.md + datasets/module_keys.csv
```

Three granularities (verified on 2025; the structure is stable across years):

**HOGAR — 1 row per household.** Key `conglome+vivienda+hogar`. Join 1:1.
`34 sumaria` (the anchor: carries `inghog2d`/`gashog2d`/`pobreza`/`linea`/`factor07`),
`01 vivienda_hogar`, `37 programas_sociales`, `84 participacion_ciudadana`,
`85 gobernabilidad`.

**PERSONA — 1 row per person.** Key `conglome+vivienda+hogar+codperso`. Join 1:1.
`02 miembros`, `03 educacion`, `04 salud`, `05 empleo_ingreso`,
`28 trabajadores_agro`, `25 gastos_agropecuarios`.

**ITEM — many rows per household/person.** A product/expenditure/activity per row;
the key needs an extra code. **Aggregate to hogar/persona before joining, never
the reverse.** Consumption modules key on a product code `pNNNn`
(`07 alimentos` = `+p601a`, **~267 rows/hh, ≈9.0 M rows**; `08`–`18`, `78`); the
agricultural modules key on `codperso+pNNNNa` (`22 prod_agricola`, `23`, `24`,
`26`, `27`); `77 agro_actividad_persona` is person × activity.

> **Golden rule.** Merge on the key of the **finer** of the two modules, with a
> **LEFT join anchored on the correct universe**, and print N-before/N-after.
> Never `keep if _merge==3` blindly — each module's universe differs, so an inner
> join silently deletes people (children, the out-of-universe, the non-agricultural).

### Universes differ — the merge traps

- **`01 vivienda_hogar` has 44,599 rows but `34 sumaria` has 33,702.** Module 01 is
  the **dwelling frame** (it includes incomplete/refused/absent visits, `result≠1`);
  the analytical sample is the ~33.7 k complete households. Anchor analysis on
  Sumaria, not on the dwelling list.
- **Agricultural modules (`22`–`28`, `77`) cover only ~10 k households** — the
  agricultural producers — not the full 33.7 k. Their `factor07` is absent (carry it
  from Sumaria). A naïve merge to the full sample makes them look like national
  totals; they are not.
- **`02 miembros` (everyone, 115 k), `03 educacion` (age 3+, 104 k), `05 empleo`
  (age 14+, 85 k)** are nested universes. Person-level joins between them are clean
  only because the finer module is a subset — confirm with an N-audit.

### Cross-year comparability breaks (read before pooling years)

ENAHO question codes and **definitions** drift. Some breaks are silent — the variable
name and label stay identical while the concept changes; others change the code while
keeping the concept. **Before using any `pNNN` in a time series, verify the code → concept
mapping is stable across *every* year, not just the endpoints.** A label can also be
*wrong* in a single year while the variable is fine — so verify three ways: the
questionnaire PDF, the column label, and the empirical weighted distribution.

The **complete, classified catalog of every break is in
[`docs/INCONSISTENCIES.md`](docs/INCONSISTENCIES.md)** (🔴 real / 🟠 bounded / 🟢 label
noise, each with how it is handled). Tools:

```bash
python audit_modules.py                       # cross-year code-stability audit (curated battery)
python audit_modules.py educacion 03 p301a    # one variable: distinct schemes by year
python verify_codes.py participacion_ciudadana 84 p801_1   # value-labels per year, flags drift
```

The most consequential breaks:

| Variable | Break | Handling |
|---|---|---|
| **M18 `p612n`** (durables) | Codes renumbered in 2007–2010 (Refri 4→12, PC 20→7, Lavadora 8→13, Auto 15→17…) | Per-scheme map `code_for(name,year)`; `NOTES_m18_codigos.md` |
| **M22 `p21002*`** (agro destino) | Venta/autoconsumo/total block only exists 2011+ | Series starts 2011 |
| **M84 `p801_*`** (participation) | Org codes 1–12 stable, **13+ shift** old↔new scheme; "no pertenece" 18→19; name only in PDF | Series on codes 1–12; `NOTES_m84_codigos.md` |
| **M37 `p710_*`** (programs) | **Two breaks:** (a) suffix renumbered — `Juntos` = `p710_03` in 2013 but `p710_04` 2014+ (Wawa Wasi split bumped it); Pensión 65 = `p710_05` all years. (b) Format switches 2021–2024 to **long** (`p712` value-labels, no "did-not-receive" rows). | **Resolved** → clean Juntos/Pensión 65 series 2013–2025. Map read per-year from each zip's `700b` value-labels + `CED-01-700A`; denominator anchored on Sumaria (all households). `NOTES_validacion_externa.md §3b` |
| **M85 trust `p1_*`** | Module absent 2004–06 & 2012–13; no labels 2011 | Trust series starts 2007 |
| **Internet `p1144`** (M01) | 2023 concept widens (household connection → access by any means incl. mobile) → 55%→90% jump | Plotted discontinuous; fixed-internet `p114b1` only ~30% |
| **Industry `p506`→`p506r4`** (M05) | CIIU rev3 → rev4 | Map both revisions |
| **M03 `p300a`** (mother tongue) | "English" (5) dropped after 2013; code 8 redefined + 9 added 2018 | Indigenous codes 1–3 stay comparable |
| **M03 `p301a`** (education) | Codes 1–11 stable; code 12 "básica especial" added 2017 | Years-of-schooling dict valid |
| **M04 availability windows** (Salud) | Same module, vars enter/leave: parto `p401a/b` only 2007–2010; disability `p401h1-6` and migration `p401f` only **2016+**; COVID symptom `p4026` only 2020+ | Per-variable series window; chronic `p401`, problem `p402*`, where-sought `p403*`, reasons `p409` **stable 2007–2025** (CED-01A-400 verified) |

> **Caveat that almost bit us:** the audit flagged `p4195` (SIS) as changing to "seguro
> universitario" in 2005 — but that was a *mislabeled value string* in that year's `.dta`;
> the variable is SIS throughout (rates 15%→31.5%→66% track the real expansion). Only the
> empirical cross-check caught the false alarm. Never trust a single source.

**Verified stable across 2004–2025** (`verify_codes.py`, safe to pool without remapping):
`ocu500` (1=ocupado), `p306`/`p307` schooling (1=sí/2=no), `pobreza` (1=extreme, 2=poor),
`p103` floor material (6=earth), `p401` chronic illness. Verifying *stability* is as much a
result as finding a break — it is what licenses the time series.

### Multi-module joins (cross-module figures)

Several figures combine modules. The golden rule (see below) holds: **LEFT-join on the
finer key, carry the right weight, audit N before/after.** Person key =
`conglome+vivienda+hogar+codperso`; household key drops `codperso`.

| Figure | Modules joined | Key | Weight | Finding |
|---|---|---|---|---|
| `fig_trabajo_adolescente_pobreza_tiempo` | **M05** work × **M34** poverty | person→household | `fac500a` | Adolescent (14–17) work halved 40%→21%; the poor/non-poor gap (15 pp in 2004) **vanished** by 2025 |
| `fig_trabajo_adolescente_escuela_tiempo` | **M05** work × **M03** school | person | `fac500a` | "Only studies" 41%→59%, "only works" 24%→9%, but **"neither" stuck at ~20%** |
| `fig_penalidad_maternidad_tiempo` | **M02** household composition × **M05** work | person + household | `fac500a` | A young child in the home lowers women's employment (~13 pp) but **raises** men's; the motherhood penalty **widened** 8→13 pp (2004→2025) |
| `fig_evento_maternidad_empleo` | **M02** household composition × **M05** work | person + household | `fac500a` | Child-penalty *event study* (employment by age of youngest child): women's employment drops at child age 0 and recovers only as the child reaches school age; men flat. **Synthetic cross-section, not within-person panel** |
| `fig_discapacidad_empleo_tiempo` | **M04** disability × **M05** work × **M34** poverty | person + household | `fac500a` | Working-age (25–59) people with a disability are employed ~30 pp less and the gap **widens** (their rate fell to ~53%); also poorer. Disability `p401h1-6` only 2016+ |
| `fig_jefatura_femenina_pobreza_tiempo` / `_share_tiempo` | **M02** headship (`p203`==1, `p207`) × **M34** poverty | household | `factor07` | Female headship rose 22%→39%; female-headed households are **consistently *less* poor** — the "feminization of poverty" does not hold in Peru (smaller households, widowhood, remittances) |
| `fig_movilidad_educativa_tiempo` | **M02** headship × **M03** education (head's `p301a` → youth attendance) | household → person | `factor07` | Higher education is **still inherited**: youth (17–21) whose household head has higher ed attend ~20 pp more; access rose for all but the gap by parental education barely moved in 20 years |
| `fig_brecha_ingreso_etnico_tiempo` | **M05** labour income × **M03** mother tongue | person | `fac500a` | Indigenous earnings gap is mostly **education, not pay**: raw ratio rose 68%→92%, but *within higher education* it was already at parity (~100%) throughout — unlike the gender gap |
| `fig_busqueda_atencion_salud_tiempo` | **M04** utilisation × own insurance | person | `factor07` | SIS coverage 15%→66% but professional consultation among the sick flat at ~⅓ |
| `fig_who_trusts_state` / confianza-por-grupo | **M85** trust × **M02/M03** demographics | person | `factor07` (Sumaria) | Trust gradients by education, ethnicity, age |

Adolescent-labor caveat: M05 starts at age 14, so this is **adolescent** labour (14–17),
not full child labour (5–17). Documented per figure in `NOTES_validacion_externa.md` (§3b–§3f).

The full per-variable type/label matrix (which years, which type, which label) is also
auto-generated:

```bash
python track_variables.py --modules 34 85
```

---

## Usage

```bash
cd scripts

# one-time / refresh: pull everything
python download_enaho.py --all --modules 01 02 03 04 05 34 85

# routine update (only grabs what is missing locally)
python download_enaho.py --update

# a brand-new year not yet mapped? find its code, then add one line to enaho_codes.py
python download_enaho.py --discover 2026

# map how variables/questions change across years (string vs numeric, label, presence)
python track_variables.py --modules 34 85

# build a purpose dataset and a figure
python dataset_income.py
python fig_map_income.py        # district choropleth, 2021 vs 2025 + change
```

---

## Reproducing official statistics

ENAHO estimates are **weighted**. Always use the expansion factor `factor07`
(household) from `sumaria`. Poverty headcount, mean income, etc. must be computed
as `factor07`-weighted means. The `dataset_*` builders carry the weight through so
the toolkit reproduces INEI's published poverty rate and income levels.

## Real (deflated) income

`sumaria` income (`inghog2d`) is already spatially deflated to each year's prices.
To compare **across years** (e.g. 2021 vs 2025) it is further deflated to a common
base year using INEI CPI — see `scripts/build_deflators.py`. All cross-year income
figures in `datasets/` and `figures/` are in **constant soles** of the stated base.

---

## Variable / question change tracker

ENAHO question codes drift across years (e.g. industry coding `p506` → `p506r4`
under CIIU rev3→rev4; variables switch between **string and numeric**). `docs/`
holds an auto-generated matrix: for every variable, in which years it appears, its
type each year, and its label. This is the map you consult before pooling years.

---

_Workspace created 2026-06. Source archive: `D:\Shining Path and Geographic\ENAHO`._
