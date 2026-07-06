"""Department centroids (lon, lat) for flow-map anchors, from the INEI shapefile.
Output: frontend/public/geo/dept_centroids.json  {name: [lon, lat]}
Run:  py -3.14 build_centroids.py
"""
import json
from pathlib import Path

import geopandas as gpd

import geo_dept as gd

HERE = Path(__file__).resolve().parent
SHP = Path(r"D:\Shining Path and Geographic\Final Results\Figures\Limite Distrital INEI 2025 CPV.shp")
OUT = HERE.parent / "frontend" / "public" / "geo" / "dept_centroids.json"


def main():
    g = gpd.read_file(SHP)
    g["UBIGEO"] = g["UBIGEO"].astype(str).str.zfill(6)
    g["code"] = g["UBIGEO"].str[:2]
    g = g.to_crs(4326)
    dep = g.dissolve("code")[["geometry"]].reset_index()
    # representative_point is guaranteed inside the (possibly concave) polygon
    dep["pt"] = dep["geometry"].representative_point()
    out = {}
    for _, r in dep.iterrows():
        name = gd.CODE2NAME.get(r["code"])
        if name:
            out[name] = [round(r["pt"].x, 4), round(r["pt"].y, 4)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(out)} department centroids")
    print("sample:", dict(list(out.items())[:3]))


if __name__ == "__main__":
    main()
