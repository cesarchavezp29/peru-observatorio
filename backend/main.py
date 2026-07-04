"""Observatorio de Datos del Peru - FastAPI backend.

Serves a dynamic query API over the DuckDB analytical database and (in
production) the built React frontend as static files.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

import db

app = FastAPI(title="Observatorio de Datos del Peru", version="0.1.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# --------------------------------------------------------------- catalog API
@app.get("/api/databases")
def get_databases():
    return db.databases()


@app.get("/api/databases/{schema}")
def get_database(schema: str):
    if schema not in db.DATABASES:
        raise HTTPException(404, "database not found")
    return {"database": db.DATABASES[schema], "themes": db.themes(schema)}


@app.get("/api/tables/{schema}/{table}")
def get_table_meta(schema: str, table: str):
    if not db.valid_table(schema, table):
        raise HTTPException(404, "table not found")
    meta = db.CATALOG[(schema, table)]
    return {**meta, "column_types": db.columns(schema, table)}


@app.get("/api/distinct/{schema}/{table}/{col}")
def get_distinct(schema: str, table: str, col: str):
    try:
        return {"values": db.distinct(schema, table, col)}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ----------------------------------------------------------------- data API
@app.get("/api/data/{schema}/{table}")
def get_data(
    schema: str, table: str,
    cols: str | None = Query(None, description="comma-separated columns"),
    order: str | None = None,
    desc: bool = False,
    limit: int = 5000,
    offset: int = 0,
    filters: str | None = Query(None, description="JSON list of {col,op,val}"),
):
    col_list = [c.strip() for c in cols.split(",")] if cols else None
    filt = None
    if filters:
        try:
            filt = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(400, "filters must be valid JSON")
    try:
        return db.fetch(schema, table, cols=col_list, filters=filt,
                        order=order, desc=desc, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/download/{schema}/{table}.csv")
def download_csv(schema: str, table: str):
    try:
        res = db.fetch(schema, table, limit=50000)
    except ValueError as e:
        raise HTTPException(404, str(e))

    def gen():
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=res["columns"])
        w.writeheader()
        yield buf.getvalue()
        for row in res["rows"]:
            buf.seek(0); buf.truncate(0)
            w.writerow(row)
            yield buf.getvalue()

    return StreamingResponse(
        gen(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{table}.csv"'},
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "tables": len(db.CATALOG),
            "databases": list(db.DATABASES)}


# --------------------------------------------------------- serve frontend
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="app")
