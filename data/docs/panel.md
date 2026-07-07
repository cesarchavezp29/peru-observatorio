# ENAHO Panel (longitudinal) — toolkit notes

Companion to the cross-section toolkit. The **ENAHO Panel** re-interviews a FIXED
subset of households across several consecutive years, so it supports true
within-household / within-person estimation (poverty dynamics, transitions,
fixed effects, event studies) — not the synthetic pseudo-panels the annual
cross-section forces.

Everything below was verified live against the INEI server + the file metadata on
2026-06-19. Single sources of truth in code: `scripts/panel_codes.py` (codes +
module maps) and `scripts/panel_io.py` (wide→long reshape).

---

## 1. Proyecto codes (release year → INEI code)

The panel is a SEPARATE set of INEI "proyectos" from the annual survey; the codes
are interleaved with the cross-section. Release year = the LAST wave each file
covers.

| release | code | waves covered | release | code | waves covered |
|--|--|--|--|--|--|
| 2011 | 302 | 2007–2011 | 2019 | 699 | 2015–2019 |
| 2015 | 529 | 2011–2015 | 2020 | 743 | 2016–2020 |
| 2016 | 614 | 2012–2016 | 2021 | 763 | 2017–2021 |
| 2017 | 612 | 2015–2017 | 2022 | 845 | 2018–2022 |
| 2018 | 651 | 2015–2018 | 2023 | 912 | 2019–2023 |

Source: INEI microdata catalogue, cross-checked against the `dopatendo/enaho` R
package `codigosencuesta.rds`. Wave spans confirmed empirically (the `_NN` year
suffixes inside each Modulo file).

**The releases are OVERLAPPING 5-year windows, not one continuous panel.** E.g.
2011–2015 and 2012–2016 share 2012–2015. Each release is its OWN independently
balanced panel with its OWN longitudinal weights. Do not naively stack releases as
if a household keeps the same id across releases — the panel id is only stable
WITHIN a release.

## 2. Two module-numbering schemes (the trap)

Unlike the cross-section, the panel does NOT use the 01/02/03… module numbers
uniformly. There are two eras (download URL = `…/STATA/{code}-Modulo{NN}.zip`):

* **OLD scheme — releases 2011, 2015, 2016, 2017** — small modules are
  ZERO-PADDED 2-digit (note: `Modulo1`/`Modulo5` return 404; padding required):
  - `01` vivienda/hogar · `03` educación · `04` salud · `05` empleo+ingresos
  - `34` sumaria (variables calculadas) · `1314` miembros del hogar (2016–2017 only)
* **NEW scheme — releases 2018–2023** — a contiguous `1474..1479` block, used
  as-is (no padding):
  - `1474` vivienda/hogar · `1475` educación · `1476` salud · `1477` empleo+ingresos
  - `1478` sumaria · `1479` miembros del hogar

`panel_codes.modules_for(release)` returns the right set per era.
There is NO module 02 in the old panel; household members come from `1314`
(2016–17) or `1479` (new era).

## 3. Physical layout: WIDE, not long

Every panel module file is **WIDE**: one row per panel unit, with variables
suffixed by 2-digit year — `p101_07`, `p101_08`, …, `ubigeo_11`. The year
suffix `NN` → `2000+NN`. The longitudinal anchor columns carry NO suffix.

`scripts/panel_io.load_long(path)` detects the layout and melts `_NN` suffixes
into a tidy long panel with an `anio` column. Verified on the 2007–2011 M01:
113,995 households × 1511 cols → 569,975 rows (113,995 × 5 waves), zero duplicate
ids per wave.

**Longitudinal keys (no suffix, constant across waves) — and they DRIFT by release:**
* OLD releases (2011, 2015): household `cong + vivi + num_hog` (a constant panel
  household number).
* NEWER releases (2016, 2017, 2018, …): there is NO constant `num_hog`; the tracked
  unit is the DWELLING `conglome + vivienda` and the household `hogar_NN` is
  per-wave. `build_panel_dataset._anchors()` auto-detects the scheme and normalizes
  `conglome/vivienda → cong/vivi` so releases stack.
* Person (M03/M04/M05): `cong + vivi + p201p` — `p201p` is the stable person-panel
  id. The per-wave household location is `con_NN/viv_NN/hog_NN`, per-wave person
  code `codp_NN`.

**Weight name drifts too:** the longitudinal weight is `fac_panel<window>` (2011-16),
`facpanel<window>` (2017), or `facpan<window>` (2019+). Cross-sectional weight is
`fac_NN` (old) / `factor07_NN` (newer) / bare `factor07` (terminal wave). Membership
flags: `hpan<win>` → `hpanel_<win>` → `hpanel_YY_YY`(+`s`). All in `panel_keys`; verify
the column EXISTS per release, never hardcode a spelling.

⚠️ **A person file can SHIP the membership flag but NOT the longitudinal weight** — the
2019 salud (M04) file has only `factor07_NN` (cross-sectional) + `perpanel_1519` flags,
no `facpan`. The weight is NOT missing: it lives in that release's **Sumaria**
(`facpan1519`, a household weight). `panel_keys.hh_panel_weight(release_dir, win)` reads
it and merges onto the person rows by the dwelling key (conglome+vivienda) — do this
rather than skip the window. (Caught 2026 when 2015-19 salud first looked weightless.)

⚠️ **The stable person id `p201p` is NOT in every person module — DO NOT join person
files on it.** (Caught 2026-06-20 building the child-penalty event study, when 3 of 8
releases silently dropped out.) The spelling and even the *presence* of the panel
person id drift by release **and by module**:
* roster (`200`/`1314`): `p201p` — but **constant/unsuffixed** in 2013-2017, **suffixed**
  `p201p_NN` in 2012-2016 & 2019-2023, and `p201pcor` in 2015-2019;
* empleo (`500`): **2013-2017 carries NO panel id at all**; 2015-2019 has only
  `p201pcor`; 2019-2023 has `p201p_NN`.

So a `p201p`-keyed merge silently yields zero rows on the releases that lack it. The
robust key that EVERY release/module carries is the **per-wave person locator**
`conglome + vivienda + anio + hogar_NN + codperso_NN`. Build the long panel on that
locator, then attach the stable `p201p` from the **roster** (coalescing
`p201p`←`p201pcor`) via the same locator, and follow the person across waves by that
attached `p201p`. `panel_evento_hijo_empleo._melt_waves` / `process_release` implement
this. Same discipline as the weight/flag drift: **verify the id column exists per
release, never hardcode a spelling.**

**Scope (swept 2026-06-20):** this trap only bites scripts that **cross-join two person
modules** (the event study joins roster births ↔ empleo). The within-file scripts
(`panel_empleo_informalidad`, `panel_salud_seguro`, `panel_intergen_*`,
`panel_movilidad_ingreso`) read a SINGLE wide module where each row already is one person
across all waves, so they track the person by the row itself and merge only on the
DWELLING key (`cong/vivi`, to attach the sumaria weight) — never on `p201p`. Verified
they all produce sane outputs for the 3 once-broken releases (2013-17, 2014-18, 2015-19).
No fix needed there.

⚠️ Memory: the 6–8 GB wide M04/M05 files do NOT fit a full pandas load (~20 GB
RAM). Always read with `usecols=` the few columns you need. `inspect_panel.py`
is metadata-only by design.

## 4. Balanced sub-panels and INEI longitudinal weights

INEI ships, inside each release's sumaria/person file:
* membership flags `hpan<window>` (households) / `pan<pair>` and
  `perpanel<window>` (persons) — `==1` if the unit is in that balanced window;
* longitudinal expansion weights `fac_panel<window>` (households) /
  `perpanel<window>` weight (persons).

`<window>` is the 4-digit `YYWW` span, e.g. `0711` = 2007–2011 (the full 5-wave
balanced panel), plus every shorter sub-window (`0708`, `0809`, … pairs).

Each sumaria ALSO carries a **per-wave cross-sectional weight** — `fac_NN` (old
releases) or `factor07_NN` / bare `factor07` for the terminal wave (newer) — which
is a DIFFERENT object from the longitudinal `fac_panel<window>`.

**Use the right weight for the question:**
* annual marginal (poverty/income for one year) → FULL per-wave sample ×
  `fac_NN`/`factor07_NN`, person-expanded by `mieperho`;
* dynamics (chronic/transient, transitions, FE) → balanced window via `hpan`/
  `perpanel` flag × `fac_panel<window>`/`perpanel` weight.

Longest balanced panel per release (households): 2007–11 → 1,129; 2011–15 → 2,174;
2012–16 → 1,006; 2013–17 → 1,784. (Smaller than the cross-section because attrition
compounds over 5 waves.)

Poverty coding is the standard `pobreza`: 1=pobre extremo, 2=pobre no extremo,
3=no pobre → poor = `pobreza in {1,2}`. Income `inghog2d`, expenditure `gashog2d`,
poverty line `linea`, extreme line `linpe`, household size `mieperho`.

## 5. Pipeline / scripts

| script | role |
|--|--|
| `panel_codes.py` | codes + two-era module maps (+ harvested ENDES codes 1996–2024) |
| `panel_download.py` | download every release × era-modules; extract ALL .dta; verify; manifest `raw/panel/_panel_manifest.csv` |
| `inspect_panel.py` | metadata-only structure map → `docs/PANEL_STRUCTURE.md` + `datasets/panel_file_keys.csv` |
| `panel_io.py` | `load_long()` — detect WIDE/LONG, reshape to tidy long panel |
| `panel_pobreza_dinamica.py` | flagship: chronic/transient/never poverty + entry/exit transition rates |
| `panel_validate.py` | validation gate (per-wave marginal vs official; survivor diagnostic) |
| `build_panel_dataset.py` | **the analysis-ready artifact** → `datasets/enaho_panel_hogar_long.parquet` |
| `fig_panel_validation.py` | calibration plot (marginal on the 45° line, longitudinal off it) |
| `panel_empleo_informalidad.py` | person-level informality dynamics (chronic/transitional, formaliz./informaliz.) |
| `panel_evento_hijo_empleo.py` | **child-penalty event study** — TRUE within-person, the panel analogue of the cross-section pseudo-panel `fig_evento_maternidad_empleo.py` |

**The dataset `datasets/enaho_panel_hogar_long.parquet`** is the tidy long
household panel: one row per (release, household, wave), columns `release, window,
hhid, cong, vivi, num_hog, anio, pobreza, poor, inghog2d, gashog2d, linea, linpe,
mieperho, dominio, estrato, w_xsec, w_panel, in_balanced`. **`hhid` is stable WITHIN
a release only** (releases are independent overlapping panels). Use `w_xsec` for
annual marginals, filter `in_balanced==1` + use `w_panel` for dynamics.

⚠️ **FRAME vs PANEL — do not confuse the two (the row count is deceptive).** The full
10-release file is ~1.62M household-wave rows, which looks cross-section-sized. It is
NOT 1.6M panel households. ENAHO is a ROTATING panel: ~35k households/year, a subset
stays up to 5 years, so the 5-year UNION per release is ~87k–133k households (the
*frame*). Only **~1,000–2,000 households per release are balanced** (interviewed all 5
waves, `in_balanced==1`). Across all 10 overlapping windows the balanced set is 87,635
household-wave rows / 17,464 unique household-windows. The file keeps the whole frame
on purpose: the full sample × `w_xsec` reproduces official annual poverty (validation),
while every DYNAMICS analysis (chronic/transient, transitions, mobility) filters to
`in_balanced==1` × `w_panel`. So "1.62M rows" = the container; "the panel" = ~2k
balanced households per window.

Data lands in `raw/panel/<release>_<code>/<INEI_filename>.dta` (gitignored).
Figures in `figures/13_panel/`.

## 6. Findings so far

**Poverty dynamics, 2007–2011 balanced panel** (n=1,129 hh, INEI `fac_panel0711`):
the static 34% annual poverty rate is NOT a fixed poor third. Over 5 years:
- 43% never poor, 57% poor at least once,
- only **14.5% chronic** (poor all 5 years),
- **42.5% transient** (churn in and out).

Entry rate (non-poor→poor) ~11–12%/yr; exit rate (poor→non-poor) ~27–34%/yr.
Exit ≫ entry ⇒ poverty is far more rotational than permanent — a conclusion no
cross-section can reach. Consistent with INEI's own panel reports (chronic poverty
~12–15% for this period).

**Persistence across windows** (`fig_pobreza_persistencia_releases`, 5 windows
2007–11 … 2014–18): chronic poverty COLLAPSED 14.5% → ~4.7% during the growth boom,
while transient poverty stayed high (~31–35%) and the static annual rate fell
34%→19%. Reading: Peru largely eliminated PERMANENT poverty, but a third of
households still churn in and out — poverty became **vulnerability, not
destitution**. Caveat: windows overlap (not independent); 2007–11 has the smallest
balanced n (1,129) and the highest base. Extends naturally into the COVID era as the
2016–20 / 2018–22 / 2019–23 releases finish downloading.

**Validation gate (`panel_validate.py`, `fig_panel_validation_pobreza`):** the FULL
per-wave sample weighted by the per-wave cross-sectional weight reproduces official
INEI national poverty to **0.00pp across all 20 downloaded waves** → the panel
microdata is sound. The balanced-survivor poverty (longitudinal weight) deviates by
±several pp, sign varying by release — survivor composition, a diagnostic, not an
error. ⚠️ LESSON: an earlier pass used the longitudinal weight to reproduce an
*annual* marginal, saw a 2.6pp gap, and nearly logged it as "expected drift." It was
the wrong weight on the wrong sample. Investigate the method before calling a
validation gap "expected." (Mirrored in the README.)

## 6b. Person-level dynamics (the panel's reason to exist)

Beyond the household sumaria, the panel's person modules (empleo M05/1477, educación
M03/1475, salud M04/1476) let us follow the SAME person across waves via
`cong+vivi+p201p`. `panel_keys.person_*` helpers detect the person key, the person
balanced flag `perpanel<window>` (spellings drift like the household ones), and reuse
the household longitudinal weight `fac_panel<window>` carried onto persons.

**Informality dynamics** (`panel_empleo_informalidad.py`, flagship): informality is
RECONSTRUCTED per wave with INEI's rule (same as cross-section build_informalidad:
p507 category + p511a contract + p510a/p510a1 registration; ocupinf not shipped).
Universe = workers occupied in EVERY wave. Finding (2007–11, n=1,358): static informal
77% (validates vs cross-section ~78–81%), but **64.7% are CHRONICALLY informal**
(informal all 5 waves) vs only 23% transitional. Transitions: informalización
(formal→informal) 18–25%/yr while formalización (informal→formal) only 5–9%/yr.

**THE CONTRAST that defines the panel's value:** poverty is ROTATIONAL (14.5% chronic,
exit≫entry — a risk you usually escape) while informality is a STRUCTURAL TRAP (64.7%
chronic, entry≫exit — formal jobs are fragile, informal jobs sticky). A repeated
cross-section sees only the static rates (34% poor, 77% informal) and cannot tell the
two apart. This is the headline reason to use the panel.

**Child-penalty event study** (`panel_evento_hijo_empleo.py`, 2026-06-20): the TRUE
within-person analogue of the cross-section synthetic pseudo-panel
(`fig_evento_maternidad_empleo.py`). We follow the SAME woman across waves, date the
birth of a child she heads/parents (a `hijo` aged 0 enters her household), and read her
employment (`ocu500`) by event time relative to the birth year. **Plot the BALANCED
event window e in [-2,+2] in LEVELS (% ocupado), not normalized deviations.** Two
methodology lessons from getting this wrong first:
* a within-person *normalized* (Kleven-style, anchored at e=-1) deviation chart is
  unreadable and ERASES the gender gap — both lines pass through 0 at e=-1 by
  construction, so it falsely looks like mothers "out-work" fathers pre-birth. Show
  LEVELS.
* a raw level profile over the FULL e=-3..+3 zig-zags because each event-time bin draws
  a DIFFERENT set of parents (5-wave rotating panel). Fix = the BALANCED sub-panel:
  keep only parents observed at EVERY e in the window, so the same people appear in
  every bin. n=206 mothers / 178 fathers survive e in [-2,+2].

**Finding (balanced levels):** fathers are flat at ~91-94% throughout; mothers fall from
**73.6% (e=-2) → 64.2% (e=-1, pregnancy) → 56.5% at birth (e=0)**, then recover only
partially to 59.5% / 65.1% by e=+1/+2. So (a) a large GENDER GAP in employment (~25-35pp,
fathers always above), and (b) a maternal child penalty of **-17pp from e=-2 to the birth
year**, partly persistent (still ~-8pp below the e=-2 level two years out). The father
does not move — the penalty is entirely the mother's. Caveat: releases overlap (precision
optimistic); the balanced window trades n for clean composition.

## 7. Cross-year comparability — track BEFORE any series

Same discipline as the cross-section (`verify_codes.py`, `INCONSISTENCIES.md`):
because releases are independent overlapping panels with their own id scheme,
NEVER assume a household/person id is comparable ACROSS releases. Within a
release, verify the `_NN` suffix set covers the expected waves and that the
poverty/income code→concept mapping matches the cross-section years it overlaps.
The old↔new module renumbering (01/03/04/05/34 → 1474–1479) is the headline
structural break.
