"""
inspect_modules.py - DESENTRANAR la llave de merge de cada modulo ENAHO
========================================================================
Para cada modulo presente en raw/ (un anio dado, por defecto 2025) determina
EMPIRICAMENTE su llave de union: la combinacion minima de columnas identificadoras
que hace unica cada fila. Asi se ve la GRANULARIDAD real del modulo y como se
mezcla con los demas:

  HOGAR    : unico en conglome+vivienda+hogar           (Sumaria 34, Vivienda 01, ...)
  PERSONA  : unico en conglome+vivienda+hogar+codperso  (Miembros 02, Educacion 03, ...)
  ITEM     : necesita ademas un codigo de item/producto (gastos 07-16, agro 22-28)
  OTRO     : ninguna combinacion estandar es unica (se reporta el residual)

La llave la dicta el DATO, no un comentario. Tambien se lee la etiqueta interna
del .dta (data_label de INEI) como descripcion verificada del modulo.

Salidas:
  datasets/module_keys.csv          una fila por modulo: llave, granularidad, N, etc.
  docs/MODULE_MERGE_KEYS.md         catalogo legible de llaves de merge

Run: python inspect_modules.py            # 2025
     python inspect_modules.py 2023
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DOCS = ROOT / "docs"; DOCS.mkdir(exist_ok=True)
DATA = ROOT / "datasets"; DATA.mkdir(exist_ok=True)

HH = ["conglome", "vivienda", "hogar"]            # llave hogar
PERSON = HH + ["codperso"]                          # llave persona
# columnas candidatas a "tercer nivel" (item/producto/orden) por convencion INEI
ITEM_HINTS = ["codperso", "p601a", "p607", "i524a1", "p612n", "p558c", "codigo",
              "nrofinca", "p580", "p2031", "producto", "i", "t", "norden", "item",
              "p401", "p501", "codinfor"]


def data_label(path: Path) -> str:
    try:
        with pd.io.stata.StataReader(str(path)) as r:
            return (r.data_label or "").strip()
    except Exception:
        return ""


def unique_on(df: pd.DataFrame, cols: list[str]) -> bool:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return False
    return not df.duplicated(subset=cols).any()


def find_key(df: pd.DataFrame):
    """Devuelve (llave, granularidad, extra_col_o_None)."""
    cols = set(df.columns)
    if not set(HH).issubset(cols):
        return (None, "SIN_LLAVE_HOGAR", None)
    if unique_on(df, HH):
        return (HH, "HOGAR", None)
    if "codperso" in cols and unique_on(df, PERSON):
        return (PERSON, "PERSONA", None)
    # buscar la columna extra que vuelve unica la fila (item / producto / orden)
    base = PERSON if "codperso" in cols else HH
    candidates = [c for c in df.columns if c not in base]
    # priorizar pistas conocidas, luego cualquier columna
    ordered = [c for c in ITEM_HINTS if c in candidates] + \
              [c for c in candidates if c not in ITEM_HINTS]
    for c in ordered:
        if unique_on(df, base + [c]):
            return (base + [c], "ITEM" if "codperso" in cols else "HOGAR-ITEM", c)
    return (base, "OTRO/MULTI", None)


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    rows = []
    print(f"Desentranando llaves de merge - ENAHO {year}\n" + "=" * 70)
    for mod, (folder, desc) in ec.MODULES.items():
        path = RAW / folder / f"enaho-{year}-{mod}.dta"
        if not path.exists():
            continue
        df = pd.read_stata(path, convert_categoricals=False)
        df.columns = [c.lower() for c in df.columns]
        label = data_label(path)
        key, gran, extra = find_key(df)
        n = len(df)
        nhh = df.groupby(HH).ngroups if set(HH).issubset(df.columns) else 0
        rows_per_hh = round(n / nhh, 2) if nhh else None
        keystr = "+".join(key) if key else "-"
        has_w = "factor07" in df.columns
        rows.append({"module": mod, "folder": folder, "label": label or desc,
                     "n_rows": n, "n_hogares": nhh, "rows_per_hh": rows_per_hh,
                     "granularidad": gran, "merge_key": keystr,
                     "extra_key": extra or "", "factor07": "si" if has_w else "no",
                     "n_cols": df.shape[1]})
        print(f"M{mod:>2}  {gran:11s}  key={keystr:38s}  N={n:>7,}  hh={nhh:>6,}  "
              f"x{rows_per_hh}  w={'Y' if has_w else 'n'}  | {label[:42]}")

    out = pd.DataFrame(rows).sort_values("module")
    out.to_csv(DATA / "module_keys.csv", index=False)

    # markdown
    md = [f"# ENAHO {year} - Llaves de merge por modulo\n",
          "Llave hallada EMPIRICAMENTE (combinacion minima de identificadores que hace "
          "unica cada fila). Granularidad: HOGAR (1 fila/hogar), PERSONA (1 fila/persona), "
          "ITEM (varias filas por persona/hogar: un producto, gasto u orden por fila).\n",
          "**Regla de oro:** une por la llave de la granularidad MAS FINA de los dos "
          "modulos, con LEFT join anclado en el universo correcto, y nunca `keep if "
          "_merge==3` a ciegas (cada modulo tiene su propio universo).\n",
          "| Mod | Modulo (label INEI) | Granularidad | Llave de merge | Filas | Hogares | Filas/hh | factor07 |",
          "|----|----|----|----|----:|----:|----:|:--:|"]
    for r in out.to_dict("records"):
        md.append(f"| {r['module']} | {r['label']} | **{r['granularidad']}** | "
                  f"`{r['merge_key']}` | {r['n_rows']:,} | {r['n_hogares']:,} | "
                  f"{r['rows_per_hh']} | {r['factor07']} |")
    md.append("\n## Como mezclar dos modulos\n")
    md.append("- **HOGAR x HOGAR** (ej. 01 Vivienda x 34 Sumaria): join 1:1 en "
              "`conglome+vivienda+hogar`.")
    md.append("- **PERSONA x PERSONA** (ej. 02 x 03 x 04 x 05 x 85): join 1:1 en "
              "`conglome+vivienda+hogar+codperso`.")
    md.append("- **PERSONA x HOGAR** (ej. 85 encuestado x 34 ingreso): broadcast del "
              "dato de hogar a la persona por la llave hogar (m:1).")
    md.append("- **ITEM x ...**: primero AGREGA el modulo-item a hogar/persona "
              "(sum/mean del gasto o produccion) y recien ahi une; nunca al reves.")
    (DOCS / "MODULE_MERGE_KEYS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nOK -> datasets/module_keys.csv  +  docs/MODULE_MERGE_KEYS.md  "
          f"({len(out)} modulos)")


if __name__ == "__main__":
    main()
