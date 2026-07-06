"""Dissolve the INEI district shapefile to ~196 provinces and export a compact
GeoJSON (EPSG:4326, simplified) for ECharts, plus a province code->name lookup
for the backend. Province code = CCDD + CCPP (4 digits).

Run:  py -3.14 build_geojson_prov.py
Outputs:
  frontend/public/geo/peru_provinces.geojson   (name = province, unique)
  province_names.json                           (code4 -> province name)
"""
import json
from pathlib import Path

import geopandas as gpd

HERE = Path(__file__).resolve().parent
SHP = Path(r"D:\Shining Path and Geographic\Final Results\Figures\Limite Distrital INEI 2025 CPV.shp")
OUT = HERE.parent / "frontend" / "public" / "geo" / "peru_provinces.geojson"
NAMES = HERE / "province_names.json"
TOL = 0.006  # ~0.7 km


def titlecase(s: str) -> str:
    return " ".join(w.capitalize() for w in str(s).split())


def main():
    if not SHP.exists():
        raise SystemExit(f"shapefile not found: {SHP}")
    g = gpd.read_file(SHP)
    g["UBIGEO"] = g["UBIGEO"].astype(str).str.zfill(6)
    g["prov"] = g["UBIGEO"].str[:4]
    g = g.to_crs(4326)

    # province name (+ dept for disambiguation only if a bare name repeats)
    meta = g.dropna(subset=["PROVINCIA"]).groupby("prov").agg(
        prov_name=("PROVINCIA", "first"), dep=("DEPARTAMEN", "first")).reset_index()
    meta["prov_name"] = meta["prov_name"].map(titlecase)
    dup = meta["prov_name"].duplicated(keep=False)
    meta.loc[dup, "prov_name"] = meta.loc[dup].apply(
        lambda r: f"{r['prov_name']} ({titlecase(r['dep'])})", axis=1)
    code2name = dict(zip(meta["prov"], meta["prov_name"]))

    prov = g.dissolve("prov")[["geometry"]].reset_index()
    prov["geometry"] = prov["geometry"].simplify(TOL, preserve_topology=True)
    prov["name"] = prov["prov"].map(code2name)
    prov = prov.dropna(subset=["name"]).sort_values("prov")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "features": []}
    for _, r in prov.iterrows():
        fc["features"].append({
            "type": "Feature",
            "properties": {"name": r["name"], "code": r["prov"]},
            "geometry": r["geometry"].__geo_interface__,
        })
    OUT.write_text(json.dumps(fc), encoding="utf-8")
    NAMES.write_text(json.dumps(code2name, ensure_ascii=False), encoding="utf-8")

    names = [f["properties"]["name"] for f in fc["features"]]
    print(f"wrote {OUT.name}: {len(names)} provinces, {OUT.stat().st_size/1024:.0f} KB")
    print(f"unique names: {len(set(names))}/{len(names)}")


if __name__ == "__main__":
    main()
