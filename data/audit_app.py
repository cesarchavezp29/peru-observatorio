"""Full audit of the Observatorio DB: data sanity + presentation smells.
Run: py -3.14 audit_app.py
"""
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geo_dept as gd

con = duckdb.connect(str(Path(__file__).resolve().parent / "observatorio.duckdb"), read_only=True)

TEMPORAL = ("year", "anio", "ano", "ym", "periodo", "trimestre", "window", "label")
COUNT_LIKE = re.compile(r"^(n|nn|obs|count|total|wt|peso|pop|poblacion|population|id|codigo|cod|code|cluster|caseid)$", re.I)
LONG_MARK = {"indicator", "indicador", "variable", "value", "valor", "concepto"}
DEPT_COLS = {"dep", "ccdd", "departamento", "dpto", "depto", "region", "ubigeo_dep"}

cat = con.execute("SELECT schema, table_name, title, columns, n_rows FROM meta.catalog ORDER BY schema, table_name").fetchall()

internal, longfmt, dept_x, count_def, cryptic, map_issues = [], [], [], [], [], []

def guess_x(cols):
    low = [c.lower() for c in cols]
    for k in TEMPORAL:
        for i, c in enumerate(low):
            if c == k or c.startswith(k):
                return cols[i]
    for c in cols:
        # first non-obviously-numeric — approximate: first col
        return c
    return cols[0]

for schema, t, title, colstr, n in cat:
    cols = colstr.split(",")
    low = [c.lower() for c in cols]
    # internal / meta tables
    if t in ("module_keys", "panel_file_keys") or ("key" in t and "keys" in t):
        internal.append((schema, t, title))
    # long format
    if set(low) & LONG_MARK and len(cols) <= 5:
        longfmt.append((schema, t, cols))
    # dept-code x-axis (bar view shows codes)
    x = guess_x(cols)
    if x.lower() in ("dep", "ccdd", "dpto", "depto") and not any(c.lower() in TEMPORAL for c in cols):
        dept_x.append((schema, t, x))
    # cryptic column names (short codes like p710_04, cob_peso, va_x_trab)
    cryptics = [c for c in cols if re.match(r"^p\d{3}", c) or "_x_" in c or c in ("cob_peso", "va", "vbp")]
    if cryptics:
        cryptic.append((schema, t, cryptics[:5]))

# mappable match audit
mappable = []
for schema, t, title, colstr, n in cat:
    cols = colstr.split(",")
    dc = next((c for c in cols if c.lower() in DEPT_COLS), None)
    if not dc:
        continue
    vals = [r[0] for r in con.execute(f'SELECT DISTINCT "{dc}" FROM {schema}.{t} WHERE "{dc}" IS NOT NULL').fetchall()]
    matched = sum(1 for v in vals if gd.canonical(v) is not None)
    rate = matched / len(vals) if vals else 0
    mappable.append((schema, t, dc, len(vals), matched, rate))

def show(title, rows, fmt):
    print(f"\n{'='*70}\n{title}  ({len(rows)})\n{'='*70}")
    for r in rows:
        print("  " + fmt(r))

show("INTERNAL / META tables (should NOT be user indicators)", internal, lambda r: f"{r[0]}.{r[1]}  '{r[2]}'")
show("LONG-FORMAT tables (won't chart well with auto x/series)", longfmt, lambda r: f"{r[0]}.{r[1]}  cols={r[2]}")
show("DEPT-CODE x-axis (bar shows 1..25 not names)", dept_x, lambda r: f"{r[0]}.{r[1]}  x={r[2]}")
show("CRYPTIC column names", cryptic, lambda r: f"{r[0]}.{r[1]}  {r[2]}")

print(f"\n{'='*70}\nMAPPABLE tables — dept match rate\n{'='*70}")
for schema, t, dc, nv, m, rate in sorted(mappable, key=lambda x: x[5]):
    flag = "  <-- LOW MATCH" if rate < 0.8 else ""
    print(f"  {rate*100:5.1f}%  {schema}.{t} (col={dc}, {m}/{nv}){flag}")
