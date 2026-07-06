"""Read-only DuckDB access layer for the Observatorio API.

All table/column names are validated against the in-memory catalog before they
touch SQL, and every value goes in as a bound parameter, so the dynamic query
endpoints cannot be used for injection.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "observatorio.duckdb"

_con = duckdb.connect(str(DB_PATH), read_only=True)
_lock = threading.Lock()

# ------------------------------------------------------------------ catalog
DATABASES: dict[str, dict] = {}
CATALOG: dict[tuple[str, str], dict] = {}   # (schema, table) -> meta
_COLS: dict[tuple[str, str], dict[str, str]] = {}  # (schema, table) -> {col: type}
_DEPT: dict[tuple[str, str], str] = {}      # (schema, table) -> dept column
_TEMPORAL: dict[tuple[str, str], str] = {}  # (schema, table) -> temporal column
_CATEGORY: dict[tuple[str, str], str] = {}  # (schema, table) -> long-format category col
_PROV: dict[tuple[str, str], tuple[str, bool]] = {}  # (schema,table) -> (col, is_ubigeo)
_PROV_NAMES: dict[str, str] = {}            # province code (4-digit) -> name


def _isnum(ty: str) -> bool:
    return any(k in (ty or "").upper() for k in
               ("INT", "DOUBLE", "DECIMAL", "FLOAT", "REAL", "NUMERIC", "HUGEINT"))

_TEMPORAL_KEYS = ("anio", "ano", "year", "ym", "periodo", "trimestre")


def _load_catalog() -> None:
    # database-level metadata lives in the python catalog module (build-time)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
    import catalog as cat  # noqa
    import geo_dept as _gd  # noqa
    globals()["gd"] = _gd
    try:
        pn = Path(__file__).resolve().parent.parent / "data" / "province_names.json"
        _PROV_NAMES.update(json.loads(pn.read_text(encoding="utf-8")))
    except Exception:
        pass
    for s, meta in cat.DATABASES.items():
        DATABASES[s] = {"schema": s, **meta}

    rows = _con.execute(
        "SELECT schema, table_name, source_file, theme_key, theme_label, "
        "title, n_rows, n_cols, columns FROM meta.catalog ORDER BY schema, title"
    ).fetchall()
    for r in rows:
        schema, table = r[0], r[1]
        CATALOG[(schema, table)] = {
            "schema": schema, "table": table, "source_file": r[2],
            "theme_key": r[3], "theme_label": r[4], "title": r[5],
            "n_rows": r[6], "n_cols": r[7], "columns": r[8].split(","),
        }
    # column types
    for (schema, table) in CATALOG:
        info = _con.execute(
            f"PRAGMA table_info('{schema}.{table}')"
        ).fetchall()
        cols = {row[1]: row[2] for row in info}
        _COLS[(schema, table)] = cols
        # a column named like a department is only a real dept key if its
        # values actually canonicalize (guards e.g. `dep`=dependency ratio)
        dc = gd.detect_dept_col(list(cols))
        if dc:
            vals = [v[0] for v in _con.execute(
                f'SELECT DISTINCT "{dc}" FROM {schema}.{table} '
                f'WHERE "{dc}" IS NOT NULL LIMIT 60').fetchall()]
            if vals and sum(1 for v in vals if gd.canonical(v) is not None) / len(vals) >= 0.6:
                _DEPT[(schema, table)] = dc
        # province-keyed tables (a `prov` 4-digit code or a `ubigeo` 6-digit
        # code aggregated to province) -> province choropleth
        if (schema, table) not in _DEPT and _PROV_NAMES:
            low = {c.lower(): c for c in cols}
            pcol = low.get("prov") or low.get("ubigeo")
            if pcol:
                is_ubi = pcol.lower() == "ubigeo"
                pvals = [v[0] for v in _con.execute(
                    f'SELECT DISTINCT "{pcol}" FROM {schema}.{table} '
                    f'WHERE "{pcol}" IS NOT NULL LIMIT 80').fetchall()]

                def _p4(v, _u=is_ubi):
                    s = str(v).split(".")[0].zfill(6 if _u else 4)
                    return s[:4]
                if pvals and sum(1 for v in pvals if _p4(v) in _PROV_NAMES) / len(pvals) >= 0.6:
                    _PROV[(schema, table)] = (pcol, is_ubi)
        for c in cols:
            if c.lower() in _TEMPORAL_KEYS:
                _TEMPORAL[(schema, table)] = c
                break
        # long-format category dimension: an explicit indicator column, or a
        # low-cardinality string column that repeats the temporal/dept axis
        # (e.g. `sector` in a year×sector table) -> needs a selector to chart.
        tcol = _TEMPORAL.get((schema, table))
        dcol = _DEPT.get((schema, table))
        n = CATALOG[(schema, table)]["n_rows"]
        low = {c.lower() for c in cols}
        is_flow = ({"origen", "source", "desde"} & low) and ({"destino", "target", "hacia"} & low)
        cat = next((c for c in cols if c.lower() in
                    ("indicator", "indicador", "variable", "concepto")), None)
        if not cat and not is_flow and (tcol or dcol) and n:
            for c, ty in cols.items():
                if c in (tcol, dcol) or _isnum(ty):
                    continue
                d = _con.execute(f'SELECT count(DISTINCT "{c}") FROM {schema}.{table}').fetchone()[0]
                if 2 <= d <= 30 and d * 1.5 < n:
                    cat = c
                    break
        if cat:
            _CATEGORY[(schema, table)] = cat


_load_catalog()

# database table counts
for s in DATABASES:
    DATABASES[s]["n_tables"] = sum(1 for (sc, _t) in CATALOG if sc == s)


# ------------------------------------------------------------------ helpers
def valid_table(schema: str, table: str) -> bool:
    return (schema, table) in CATALOG


def columns(schema: str, table: str) -> dict[str, str]:
    return _COLS.get((schema, table), {})


def databases() -> list[dict]:
    return list(DATABASES.values())


def themes(schema: str) -> list[dict]:
    """Themes within a database, each with its tables."""
    out: dict[str, dict] = {}
    for (sc, t), meta in CATALOG.items():
        if sc != schema:
            continue
        k = meta["theme_key"]
        out.setdefault(k, {"theme_key": k, "theme_label": meta["theme_label"],
                           "tables": []})
        out[k]["tables"].append({
            "table": t, "title": meta["title"], "n_rows": meta["n_rows"],
            "n_cols": meta["n_cols"], "columns": meta["columns"],
            "mappable": is_mappable(sc, t),
        })
    res = list(out.values())
    res.sort(key=lambda x: -len(x["tables"]))
    for th in res:
        th["tables"].sort(key=lambda x: x["title"])
    return res


_OPS = {
    "eq": "=", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<=",
}


def fetch(schema: str, table: str, *, cols: list[str] | None = None,
          filters: list[dict] | None = None, order: str | None = None,
          desc: bool = False, limit: int = 5000, offset: int = 0) -> dict:
    """Parameterized, whitelisted SELECT. Returns {columns, rows, types, total}."""
    if not valid_table(schema, table):
        raise ValueError(f"unknown table {schema}.{table}")
    tcols = _COLS[(schema, table)]

    sel = [c for c in (cols or []) if c in tcols] or list(tcols)
    sel_sql = ", ".join(f'"{c}"' for c in sel)

    where, params = [], []
    for f in (filters or []):
        col, op, val = f.get("col"), f.get("op", "eq"), f.get("val")
        if col not in tcols:
            continue
        if op == "in" and isinstance(val, list):
            ph = ", ".join("?" for _ in val)
            where.append(f'"{col}" IN ({ph})')
            params.extend(val)
        elif op in _OPS:
            where.append(f'"{col}" {_OPS[op]} ?')
            params.append(val)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    order_sql = ""
    if order and order in tcols:
        order_sql = f' ORDER BY "{order}" {"DESC" if desc else "ASC"}'

    limit = max(1, min(int(limit), 50000))

    with _lock:
        total = _con.execute(
            f"SELECT count(*) FROM {schema}.{table}{where_sql}", params
        ).fetchone()[0]
        cur = _con.execute(
            f"SELECT {sel_sql} FROM {schema}.{table}{where_sql}{order_sql} "
            f"LIMIT {limit} OFFSET {int(offset)}", params
        )
        data = cur.fetchall()
        names = [d[0] for d in cur.description]

    rows = [dict(zip(names, r)) for r in data]
    return {
        "schema": schema, "table": table, "columns": names,
        "types": {c: tcols[c] for c in names},
        "rows": rows, "returned": len(rows), "total": total,
    }


_CATEGORY_NAMES = ("indicator", "indicador", "variable", "concepto")


def category_col(schema: str, table: str) -> str | None:
    """The long-format category dimension (detected at load): an indicator
    column, or a low-cardinality string column that repeats the time/dept axis.
    Charting one category at a time avoids zig-zag lines across categories."""
    return _CATEGORY.get((schema, table))


_SKIP_PREVIEW = {'n', 'nn', 'n_hh', 'n_m', 'n_h', 'n_obs', 'n_depto', 'waves',
    'wt', 'wt_raw', 'cluster', 'caseid', 'codigo', 'codciudad', 'oficial',
    'pet', 'release', 'wave', 'window', 'cob_peso'}


def previews(schema: str) -> dict:
    """For each temporal table in a section, a tiny sparkline series (the first
    meaningful numeric column over time). One call powers a whole section's
    card previews."""
    out: dict[str, list] = {}
    for (s, t) in [k for k in CATALOG if k[0] == schema]:
        tcol = _TEMPORAL.get((s, t))
        if not tcol:
            continue
        cols = _COLS[(s, t)]
        val = next((c for c, ty in cols.items()
                    if c != tcol and _numeric(ty)
                    and c.lower() not in _SKIP_PREVIEW and not c.endswith('_missing')), None)
        if not val:
            continue
        try:
            res = fetch(s, t, cols=[tcol, val], order=tcol, limit=500)
        except ValueError:
            continue
        vals = [r[val] for r in res["rows"] if isinstance(r[val], (int, float))]
        if len(vals) < 3:
            continue
        if len(vals) > 60:
            step = (len(vals) + 59) // 60
            vals = vals[::step]
        out[t] = [round(v, 4) for v in vals]
    return out


def dept_col(schema: str, table: str) -> str | None:
    return _DEPT.get((schema, table))


def temporal_col(schema: str, table: str) -> str | None:
    return _TEMPORAL.get((schema, table))


def geo_level(schema: str, table: str) -> str | None:
    """'dept' for a department map, 'prov' for a province map, else None."""
    if (schema, table) in _DEPT:
        return "dept"
    if (schema, table) in _PROV:
        return "prov"
    return None


def _geo_key(schema: str, table: str) -> str | None:
    """The column used to key the choropleth (dept col or province/ubigeo col)."""
    if (schema, table) in _DEPT:
        return _DEPT[(schema, table)]
    if (schema, table) in _PROV:
        return _PROV[(schema, table)][0]
    return None


def is_mappable(schema: str, table: str) -> bool:
    """Mappable if it has a geo key (dept or province) and >=1 numeric col
    other than the geo/temporal keys."""
    gk = _geo_key(schema, table)
    if not gk:
        return False
    tcols = _COLS[(schema, table)]
    skip = {gk, _TEMPORAL.get((schema, table))}
    return any(_numeric(t) and c not in skip for c, t in tcols.items())


def _numeric(type_str: str) -> bool:
    t = (type_str or "").upper()
    return any(k in t for k in ("INT", "DOUBLE", "DECIMAL", "FLOAT", "REAL", "NUMERIC", "HUGEINT"))


def _prov_name(code, is_ubi: bool):
    s = str(code).split(".")[0].zfill(6 if is_ubi else 4)[:4]
    return _PROV_NAMES.get(s)


def map_data(schema: str, table: str, value_col: str, *,
             filters: list[dict] | None = None) -> dict:
    """Choropleth data for one numeric column, keyed by department or province
    name (averaged within each area). Province tables aggregate districts."""
    if not valid_table(schema, table):
        raise ValueError(f"unknown table {schema}.{table}")
    level = geo_level(schema, table)
    gk = _geo_key(schema, table)
    if not gk:
        raise ValueError("table has no geographic column")
    tcols = _COLS[(schema, table)]
    if value_col not in tcols:
        raise ValueError("unknown value column")
    is_ubi = level == "prov" and _PROV[(schema, table)][1]

    res = fetch(schema, table, cols=[gk, value_col], filters=filters, limit=50000)
    agg: dict[str, list[float]] = {}
    unmatched: set[str] = set()
    for row in res["rows"]:
        raw = row.get(gk)
        name = gd.canonical(raw) if level == "dept" else _prov_name(raw, is_ubi)
        if name is None:
            if raw is not None:
                unmatched.add(str(raw))
            continue
        v = row.get(value_col)
        if isinstance(v, str):
            try:
                v = float(v)
            except (TypeError, ValueError):
                v = None
        if v is None:
            continue
        agg.setdefault(name, []).append(float(v))

    data = [{"name": k, "value": round(sum(vs) / len(vs), 4)}
            for k, vs in agg.items()]
    vals = [d["value"] for d in data]
    return {
        "schema": schema, "table": table, "value_col": value_col,
        "dept_col": gk, "geo_level": level, "data": data, "n_matched": len(data),
        "min": min(vals) if vals else None, "max": max(vals) if vals else None,
        "unmatched": sorted(unmatched),
    }


def distinct(schema: str, table: str, col: str, limit: int = 500) -> list:
    if not valid_table(schema, table) or col not in _COLS[(schema, table)]:
        raise ValueError("bad column")
    with _lock:
        r = _con.execute(
            f'SELECT DISTINCT "{col}" FROM {schema}.{table} '
            f'WHERE "{col}" IS NOT NULL ORDER BY 1 LIMIT {int(limit)}'
        ).fetchall()
    return [x[0] for x in r]
