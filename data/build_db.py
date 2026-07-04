"""Build the Observatorio DuckDB from the ENAHO_ANALYSIS analytical CSVs.

Steps:
  1. copy every eligible CSV (aggregate, <8MB, not microdata) into ./datasets/
     so the app repo is self-contained and deployable
  2. load each CSV as a table inside its database schema (enaho/panel/endes/epen/eea)
  3. write a `meta.catalog` table describing every table (schema, theme, title,
     rows, columns) so the API/frontend can build navigation dynamically

Run:  py -3.14 build_db.py
"""
import shutil
import sys
from pathlib import Path

import duckdb

import catalog as cat

HERE = Path(__file__).resolve().parent
SRC = Path(r"D:\ENAHO_ANALYSIS\datasets")
LOCAL = HERE / "datasets"
DB_PATH = HERE / "observatorio.duckdb"

# In Docker/CI the original ENAHO_ANALYSIS tree is absent; build straight from
# the CSVs committed into ./datasets.
BUILD_FROM_LOCAL = not SRC.exists()


def eligible(src: Path) -> list[Path]:
    out = []
    for p in sorted(src.glob("*.csv")):
        if p.stem in cat.EXCLUDE:
            continue
        if p.stat().st_size > cat.MAX_MB * 1024 * 1024:
            print(f"  skip (microdata {p.stat().st_size/1e6:.0f}MB): {p.name}")
            continue
        out.append(p)
    return out


def main():
    LOCAL.mkdir(exist_ok=True)
    if BUILD_FROM_LOCAL:
        files = eligible(LOCAL)
        print(f"{len(files)} eligible CSVs (from local ./datasets)")
    else:
        files = eligible(SRC)
        print(f"{len(files)} eligible CSVs")
        # 1. copy into repo so it stays self-contained / deployable
        for p in files:
            dst = LOCAL / p.name
            if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
                shutil.copy2(p, dst)

    # 2. + 3. build DB
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))

    for s in cat.DATABASES:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
    con.execute("CREATE SCHEMA IF NOT EXISTS meta")

    rows = []
    seen: dict[str, str] = {}  # table_name -> file (detect collisions)
    for p in files:
        stem = p.stem
        schema = cat.schema_for(stem)
        tname = cat.table_name(stem)
        if tname in seen:
            tname = f"{tname}_{abs(hash(stem)) % 1000}"
        seen[tname] = p.name
        theme_key, theme_label = cat.theme_for(stem, schema)
        local = (LOCAL / p.name).as_posix()
        try:
            con.execute(
                f"CREATE OR REPLACE TABLE {schema}.{tname} AS "
                f"SELECT * FROM read_csv_auto('{local}', header=true, "
                f"sample_size=-1, all_varchar=false)"
            )
        except Exception as e:  # fall back to all-varchar for messy files
            con.execute(
                f"CREATE OR REPLACE TABLE {schema}.{tname} AS "
                f"SELECT * FROM read_csv_auto('{local}', header=true, all_varchar=true)"
            )
            print(f"  ! varchar fallback: {p.name} ({e})")

        info = con.execute(f"PRAGMA table_info('{schema}.{tname}')").fetchall()
        cols = [r[1] for r in info]
        n = con.execute(f"SELECT count(*) FROM {schema}.{tname}").fetchone()[0]
        rows.append({
            "schema": schema,
            "table_name": tname,
            "source_file": p.name,
            "theme_key": theme_key,
            "theme_label": theme_label,
            "title": cat.title_for(stem),
            "n_rows": n,
            "n_cols": len(cols),
            "columns": ",".join(cols),
        })

    # catalog table
    con.execute("DROP TABLE IF EXISTS meta.catalog")
    con.execute("""
        CREATE TABLE meta.catalog(
            schema VARCHAR, table_name VARCHAR, source_file VARCHAR,
            theme_key VARCHAR, theme_label VARCHAR, title VARCHAR,
            n_rows BIGINT, n_cols INTEGER, columns VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO meta.catalog VALUES (?,?,?,?,?,?,?,?,?)",
        [[r["schema"], r["table_name"], r["source_file"], r["theme_key"],
          r["theme_label"], r["title"], r["n_rows"], r["n_cols"], r["columns"]]
        for r in rows],
    )
    con.close()

    # summary
    print(f"\nBuilt {DB_PATH.name} with {len(rows)} tables:")
    from collections import Counter
    by_schema = Counter(r["schema"] for r in rows)
    for s, meta in cat.DATABASES.items():
        print(f"  {s:6s} {by_schema.get(s,0):3d} tables  - {meta['title']}")
    total_rows = sum(r["n_rows"] for r in rows)
    print(f"  total rows across analytical tables: {total_rows:,}")


if __name__ == "__main__":
    main()
