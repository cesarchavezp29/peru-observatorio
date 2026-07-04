"""Dissolve the INEI district shapefile to 25 departments and export a compact
GeoJSON (EPSG:4326, simplified) that ECharts can register as a map.

Run:  py -3.14 build_geojson.py
Output: frontend/public/geo/peru_departments.geojson
"""
import json
from pathlib import Path

import geopandas as gpd

import geo_dept as gd

HERE = Path(__file__).resolve().parent
SHP = Path(r"D:\Shining Path and Geographic\Final Results\Figures\Limite Distrital INEI 2025 CPV.shp")
OUT = HERE.parent / "frontend" / "public" / "geo" / "peru_departments.geojson"
TOL = 0.008  # degrees ~ 0.9 km; keeps shape recognizable, file small


def main():
    if not SHP.exists():
        raise SystemExit(f"shapefile not found: {SHP}")
    g = gpd.read_file(SHP)
    g["UBIGEO"] = g["UBIGEO"].astype(str).str.zfill(6)
    g["code"] = g["UBIGEO"].str[:2]
    g = g.to_crs(4326)

    dep = g.dissolve("code")[["geometry"]].reset_index()
    dep["geometry"] = dep["geometry"].simplify(TOL, preserve_topology=True)
    dep["name"] = dep["code"].map(gd.CODE2NAME)
    dep = dep.dropna(subset=["name"]).sort_values("code")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": []}
    for _, r in dep.iterrows():
        fc["features"].append({
            "type": "Feature",
            "properties": {"name": r["name"], "code": r["code"]},
            "geometry": r["geometry"].__geo_interface__,
        })
    OUT.write_text(json.dumps(fc), encoding="utf-8")

    size = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name}: {len(fc['features'])} departments, {size:.0f} KB")
    print("names:", ", ".join(f["properties"]["name"] for f in fc["features"]))


if __name__ == "__main__":
    main()
