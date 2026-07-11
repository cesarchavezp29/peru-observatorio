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
from fastapi.responses import PlainTextResponse, StreamingResponse
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


@app.get("/api/index")
def get_index():
    """Flat list of every indicator: search box + chart-type browser."""
    return [
        {"schema": s, "table": t, "title": m["title"],
         "section": db.DATABASES[s]["title"], "theme": m["theme_label"],
         "topic": m.get("topic_label"), "topic_key": m.get("topic_key"),
         "family": m.get("family"), "window": m.get("window"),
         "mappable": db.is_mappable(s, t),
         "kinds": db.kinds(s, t), "years": db.years(s, t)}
        for (s, t), m in db.CATALOG.items()
    ]


@app.get("/api/topics")
def get_topics():
    """Cross-survey topic navigation (panel families collapsed)."""
    return db.topics()


@app.get("/api/readme/{name}")
def get_readme(name: str):
    """Construction/methodology notes for a database (markdown)."""
    txt = db.readme(name)
    if txt is None:
        raise HTTPException(404, "no readme for that database")
    return PlainTextResponse(txt, media_type="text/markdown; charset=utf-8")


@app.get("/api/previews/{schema}")
def get_previews(schema: str):
    if schema not in db.DATABASES:
        raise HTTPException(404, "database not found")
    return db.previews(schema)


@app.get("/api/tables/{schema}/{table}")
def get_table_meta(schema: str, table: str):
    if not db.valid_table(schema, table):
        raise HTTPException(404, "table not found")
    meta = db.CATALOG[(schema, table)]
    return {**meta, "column_types": db.columns(schema, table),
            "dept_col": db._geo_key(schema, table),
            "geo_level": db.geo_level(schema, table),
            "temporal_col": db.temporal_col(schema, table),
            "category_col": db.category_col(schema, table),
            "mappable": db.is_mappable(schema, table)}


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


@app.get("/api/map/{schema}/{table}")
def get_map(schema: str, table: str, value_col: str,
            filters: str | None = Query(None)):
    filt = None
    if filters:
        try:
            filt = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(400, "filters must be valid JSON")
    try:
        return db.map_data(schema, table, value_col, filters=filt)
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


@app.get("/sitemap.xml")
def sitemap():
    """Every route + every chart page, so search engines can finally see us."""
    base = "https://peruobservatorio.onrender.com"
    fixed = ["", "/preguntas", "/tuvida", "/adivina", "/dibuja", "/dosperus",
             "/historia", "/desigualdad", "/quienvoto", "/graficos",
             "/movilidad", "/agenda", "/censos",
             "/comparar", "/correlacion", "/distrito", "/metodologia",
             "/datos", "/ensayos"] + [f"/tema/{k}" for k in (
                 "pobreza", "ingreso", "empleo", "educacion", "salud",
                 "sociedad", "vivienda", "agro", "empresas", "territorio")]
    urls = [f"{base}{p}" for p in fixed]
    urls += [f"{base}/db/{s}/{t}" for (s, t) in db.CATALOG]
    body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + body + "</urlset>")
    return PlainTextResponse(xml, media_type="application/xml")


@app.get("/robots.txt")
def robots():
    return PlainTextResponse(
        "User-agent: *\nAllow: /\n"
        "Sitemap: https://peruobservatorio.onrender.com/sitemap.xml\n")


# --------------------------------------------------------- serve frontend
# SPA fallback: any non-API, non-file path serves index.html so BrowserRouter
# deep links (/historia, /db/enaho/...) load directly and are crawlable.
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        from starlette.exceptions import HTTPException as StarletteHTTPException
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code == 404:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404:
            response = await super().get_response("index.html", scope)
        return response


_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", SPAStaticFiles(directory=str(_DIST), html=True), name="app")
