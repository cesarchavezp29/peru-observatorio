# EPE / EPEN toolkit (Encuesta Permanente de Empleo)

> **Análisis** (figuras, series Lima 2001-2026, mapas departamentales): ver
> [`README_EPEN_ANALISIS.md`](README_EPEN_ANALISIS.md). Este archivo cubre solo la DESCARGA.

Peru's continuous **employment** surveys, the fourth INEI track in this repo (after the
ENAHO cross-section `README.md`, the ENAHO Panel `docs/NOTES_panel.md`, and ENDES
`README_ENDES.md`). Used for high-frequency labor-market work (employment, informality,
labor income, minimum-wage bunching). Verified live 2026-06-21. Single sources of truth:
`scripts/epen_download.py` (downloader). Data lands in `raw/epen_inei/` (gitignored).

---

## 1. THE FOUR SERIES (get ALL of them, every year/period)

1. **EPE Lima Metropolitana y Callao** (legacy) — Lima-only, **since 2001**, by trimestre
   móvil; includes a **muestra PANEL** (rotating, trimestres Mar/Jun/Sep/Dic). Lima sample
   (~5k/trim). CSV name pattern `Trim <Mes-Mes-Mes><YY>` (and panel variants).
2. **EPEN Nacional** (trimestre móvil) — national, **since 2021**. ~15k/trim. Pattern
   `Trim <Mes-Mes-Mes><YY>` / `Nacional EPEN Trim. <Mes-Mes-Mes> <YYYY>`.
3. **EPEN Ciudades** — national cities, **2022+**, **annual + trimestral (Trim 1-4)**.
   Pattern `EPEN BD Ciudades Anual/Trim <YYYY>`.
4. **EPEN Departamentos** — **2022+**, **annual national + one file per department**
   (01 Amazonas, 02 Ancash, … 25 Ucayali). Pattern `EPEN <YYYY> BD_Publicacion Dpto` and
   `NN <Depto> EPEN Anual <YYYY>`.

### The EPE Lima → EPEN Lima handoff (the Lima continuation)

The legacy trimestre-móvil **EPE Lima** (#1) ends at **Jul-Ago-Set 2022**; from there Lima
Metropolitana y Callao continues under EPEN, but the FREQUENCY drops:

| | legacy **EPE Lima** | modern **EPEN Lima** |
|---|---|---|
| span | 2001 – Jul-Ago-Set 2022 | 2022 → present |
| freq | trimestre **móvil** (12 overlapping/yr) | **annual** only |
| where| codes 12/36-99/100-508/509-773 | dept file `15 Lima (incl. Callao)`: **804**=2022, **888**=2023, **949**=2024, **1015**=2025 |

There is **no standalone modern Lima *trimestral* file** — for quarterly Lima after 2022,
subset **EPEN Nacional Trim.** (4 calendar-quarters/yr, 2022-2026) by `ccdd==15`. The
moving-window Lima series is genuinely discontinued. 2022 overlaps both regimes, so no gap.

## 2. THE DOWNLOAD SCHEME — host, module, and the FORMAT-BY-ERA gotcha

All EPE/EPEN microdata is on the same srienaho host that serves ENAHO/ENDES. The employment
file is always **Modulo76** (a generic module several surveys share — filter by the file's
internal name, which identifies the series/year/period). The URL is:

    https://proyectos.inei.gob.pe/iinei/srienaho/descarga/{FORMAT}/{CODE}-Modulo76.zip
    FORMAT in {CSV, SPSS, DBF, STATA}

**datosabiertos.gob.pe blocks programmatic access (403/WAF)** — never use it; always the
srienaho host above.

### THE GOTCHA: which FORMAT a dataset ships in depends on its VINTAGE (don't probe only CSV)

Each `{CODE}-Modulo76` is published in SOME formats and 404s in the others. Two regimes:

| Era / series                                   | Codes (examples)        | Served as            | 404s on   |
|------------------------------------------------|-------------------------|----------------------|-----------|
| **Modern EPEN** 2021+ (Nacional/Ciudades/Dpto) | 740-1090                | **CSV**              | SPSS/STATA |
| **EPE Lima** 2002-2004 + 2016-2022             | 51-99, 509-773          | **CSV**              | SPSS/STATA |
| **EPE Lima** 2001 + 2004-tail + 2005-2015      | 12, 36-50, 100-508      | **SPSS (.sav) + DBF**| CSV/STATA |

So the legacy EPE Lima middle block (2001, 2005-2015) is the INVERSE of everything else:
CSV and STATA both 404, only **SPSS and DBF** exist. A CSV-only download silently leaves a
2005-2015 hole (this happened on the first pass — Carlos caught it 2026-06-22). Read `.sav`
with `pyreadstat.read_sav` (full read, NOT `usecols=` — that silently drops some files),
`.dbf` with `dbfread.DBF(p, encoding="latin-1")`.

- A few `.sav` are corrupt on the server (pyreadstat: "Invalid file / unsupported
  features") — e.g. codes **376/384** (2013 Jul-Ago-Set, Ago-Set-Oct). Fall back to the
  **DBF** for those (reads fine, same rows).
- The catalog "código de encuesta" is INEI's survey-registration id and **≠ the BDD
  download code** for old years (e.g. catalog shows 2010 = encuesta 234; here 234 IS the
  download code, but in general they diverge). Discover codes by probing, don't trust the
  catalog number.
- The inner zip-folder is sometimes named `{CODE-1}-Modulo76` (e.g. code **873** = "EPEN BD
  Ciudades Anual 2023", inner folder `872-Modulo76`) — that off-by-one is why probing 872 /
  STATA first failed.

## 3. CODE MAP (`Modulo76`, full scan 1-1090; codes are NON-chronological)

* **EPE Lima Metropolitana y Callao — trimestre móvil** (single Lima person file per
  3-month moving window; schema uses `pano`/`pmes`, NOT `anio`/`mes`):
  * `12, 36-50` → **2001-2004 boundary** (SPSS/DBF). 36-50 = 2001 (EPE launched Ago-2001).
  * `51-99` → **2002-2004** (CSV).
  * `100-508` (scattered, ~139 codes) → **2004-tail + 2005-2015** (SPSS/DBF only).
    Anchors: 100-104=2004 Q4, 117-140=2005, 142-169=2006, … 234=Nov-Dic09-Ene10,
    376/384=2013 (DBF), 483-501=2015.
  * `509-773` → **2016-2022** (CSV). Series ends Jul-Ago-Set 2022 (code 773).
* **EPEN modern 2021+** (national survey, schema uses `anio`/`mes`/`ocup300`):
  `740-1090` (~183 codes) → Nacional trimestres, Ciudades (anual+trim), Departamentos
  (national + per-dept). Anchors: 741-751 = Nacional trim 2021; 762-779 = Nacional trim
  2022-23; 870-871 = Nacional 2023-24; 873 = Ciudades Anual 2023; 874 = Dpto Nacional 2023;
  875+ = Dpto by department.

Discovered code lists are cached in `raw/epen_inei/`: `_spss_gap_codes.txt` (SPSS/Modulo76
hits 100-508), `_dbf_codes.txt` (DBF/Modulo76 hits 1-520), `_codes_all.txt` (CSV hits).

## 4. Tooling (three downloaders, by format, + one verifier)

All retry with backoff (the INEI server THROTTLES — discover in one threaded pass, then
download) and are **idempotent** (skip codes already on disk). Manifests in `raw/epen_inei/`.

* **`scripts/epen_download.py`** — **CSV** path. Discover (HEAD-probe) or `--codes-file`;
  downloads CSV+PDFs, reads the CSV label, verifies rows>0 → `_epen_manifest.csv`.
  ```
  py -3.14 epen_download.py --lo 1 --hi 1090 --modules 76      # discover + download CSV
  ```
* **`scripts/epen_legacy_spss_download.py`** — **SPSS** path for the legacy gap. Probes
  SPSS/Modulo76 over a code range (robust ranged-GET), downloads each, reads the `.sav`
  with pyreadstat, keeps EPE rows (`pano`+`pmes`), verifies rows>0 → `_epen_spss_manifest.csv`.
  ```
  py -3.14 epen_legacy_spss_download.py --lo 1 --hi 520        # fills 2001 + 2005-2015
  ```
* **`scripts/epen_dbf_fill.py`** — **DBF** fallback. Reads `_dbf_codes.txt`, pulls any
  DBF-only code not already on disk (and the corrupt-`.sav` cases like 376/384), reads with
  dbfread, identifies the window → `_epen_dbf_manifest.csv`.
* **`scripts/epen_lima_coverage.py`** — **verifier**. Keys each EPE Lima file by the actual
  `(pano,pmes)` cells INSIDE it (not the filename), reads CSV→SAV→DBF, reports missing /
  duplicate trimestre windows and a per-year count. Run after any download.

Deps: `pyreadstat` (SPSS) and `dbfread` (DBF) — both installed. Key vars: `ocup300`
employment, `ingtrabw` labor income, `informal_p` informality, `ccdd` department,
`fac300_anual`/`fac_t300` weights (modern); legacy Lima uses `pano`/`pmes` + `factor`.

## 5. Status (2026-06-22) — EPE Lima trimestre móvil COMPLETE

EPE Lima Metropolitana y Callao, trimestre móvil: **252 files, 0 gaps, 0 duplicates**,
continuous **Ago-2001 → Jul-2022** (2001=5 from Aug launch, 2002-2021 = 12/12 every year,
2022 = 7 ending Jul-Ago-Set). Verified by `epen_lima_coverage.py` against each file's
internal `(pano,pmes)`. The 2005-2015 hole left by the CSV-only first pass is closed via
the SPSS/DBF path above.

Modern EPEN (Nacional/Ciudades/Departamentos, 2021+) also downloaded (279 CSV datasets,
`_epen_manifest.csv`). (The MW/bunching paper at D:\Nexus\nexus had some EPEN ad-hoc from
datosabiertos but no reusable script — this is the reusable one.)
