"""Read-only DuckDB access layer for the Observatorio API.

All table/column names are validated against the in-memory catalog before they
touch SQL, and every value goes in as a bound parameter, so the dynamic query
endpoints cannot be used for injection.
"""
from __future__ import annotations

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

_TEMPORAL_KEYS = ("anio", "ano", "year", "ym", "periodo", "trimestre")


def _load_catalog() -> None:
    # database-level metadata lives in the python catalog module (build-time)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
    import catalog as cat  # noqa
    import geo_dept as _gd  # noqa
    globals()["gd"] = _gd
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
        dc = gd.detect_dept_col(list(cols))
        if dc:
            _DEPT[(schema, table)] = dc
        for c in cols:
            if c.lower() in _TEMPORAL_KEYS:
                _TEMPORAL[(schema, table)] = c
                break


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


def dept_col(schema: str, table: str) -> str | None:
    return _DEPT.get((schema, table))


def temporal_col(schema: str, table: str) -> str | None:
    return _TEMPORAL.get((schema, table))


def is_mappable(schema: str, table: str) -> bool:
    """A table is mappable if it has a department column and >=1 numeric col
    other than the department/temporal keys."""
    dc = _DEPT.get((schema, table))
    if not dc:
        return False
    tcols = _COLS[(schema, table)]
    skip = {dc, _TEMPORAL.get((schema, table))}
    return any(_numeric(t) and c not in skip for c, t in tcols.items())


def _numeric(type_str: str) -> bool:
    t = (type_str or "").upper()
    return any(k in t for k in ("INT", "DOUBLE", "DECIMAL", "FLOAT", "REAL", "NUMERIC", "HUGEINT"))


def map_data(schema: str, table: str, value_col: str, *,
             filters: list[dict] | None = None) -> dict:
    """Choropleth data for one numeric column, keyed by canonical department."""
    if not valid_table(schema, table):
        raise ValueError(f"unknown table {schema}.{table}")
    dc = _DEPT.get((schema, table))
    if not dc:
        raise ValueError("table has no department column")
    tcols = _COLS[(schema, table)]
    if value_col not in tcols:
        raise ValueError("unknown value column")

    res = fetch(schema, table, cols=[dc, value_col], filters=filters, limit=50000)
    agg: dict[str, list[float]] = {}
    unmatched: set[str] = set()
    for row in res["rows"]:
        name = gd.canonical(row.get(dc))
        if name is None:
            if row.get(dc) is not None:
                unmatched.add(str(row.get(dc)))
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
        "dept_col": dc, "data": data, "n_matched": len(data),
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
