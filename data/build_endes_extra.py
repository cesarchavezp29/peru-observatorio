"""Derive a few extra, weighted ENDES aggregate tables from the women microdata
so the Salud y Fertilidad section has gradients and time series, not just the
two indicator tables. Every share/mean is weighted by `wt` (=v005/1e6).

Reads the microdata from D:\\ENAHO_ANALYSIS\\datasets (not shipped in this repo)
and writes small CSVs into ./datasets. Run before build_db.py.
"""
from pathlib import Path

import duckdb

SRC = Path(r"D:\ENAHO_ANALYSIS\datasets\endes_mujeres_2004_2024.csv")
OUT = Path(__file__).resolve().parent / "datasets"
con = duckdb.connect()
W = f"read_csv_auto('{SRC.as_posix()}')"

EDUC = {0: "Sin educacion", 1: "Primaria", 2: "Secundaria", 3: "Superior"}


def q(sql):
    return con.execute(sql).df()


def main():
    if not SRC.exists():
        raise SystemExit(f"microdata not found: {SRC}")

    # 1. adolescent motherhood (15-19) by wealth quintile, pooled 2016-2024
    d = q(f"""
        SELECT CAST(riqueza AS INT) AS quintil,
          round(100.0*sum(CASE WHEN hijos_nacidos>0 OR embarazada=1 THEN wt ELSE 0 END)
                /sum(wt), 2) AS adol_madre_pct,
          count(*) AS n
        FROM {W}
        WHERE edad BETWEEN 15 AND 19 AND anio BETWEEN 2016 AND 2024
          AND riqueza IN (1,2,3,4,5)
        GROUP BY 1 ORDER BY 1
    """)
    d.to_csv(OUT / "endes_adol_maternidad_riqueza_2016_2024.csv", index=False)
    print("adol x riqueza (esperado ~20%->~3%):\n", d.to_string(index=False))

    # 2. mean children ever born by education level over time (MEF 15-49)
    d = q(f"""
        SELECT anio, CAST(educ_nivel AS INT) AS nivel,
          round(sum(hijos_nacidos*wt)/sum(wt), 3) AS ceb
        FROM {W}
        WHERE edad BETWEEN 15 AND 49 AND educ_nivel IN (0,1,2,3)
        GROUP BY 1,2 ORDER BY 1,2
    """)
    piv = d.pivot(index="anio", columns="nivel", values="ceb").reset_index()
    piv.columns = ["anio"] + [EDUC[c] for c in piv.columns[1:]]
    piv.to_csv(OUT / "endes_hijos_educacion_tiempo.csv", index=False)
    print("\nCEB x educacion (head):\n", piv.head(3).to_string(index=False))

    # 3. mean children ever born by area over time (urbano/rural)
    d = q(f"""
        SELECT anio, CAST(area AS INT) AS area,
          round(sum(hijos_nacidos*wt)/sum(wt), 3) AS ceb
        FROM {W}
        WHERE edad BETWEEN 15 AND 49 AND area IN (1,2)
        GROUP BY 1,2 ORDER BY 1,2
    """)
    piv = d.pivot(index="anio", columns="area", values="ceb").reset_index()
    piv.columns = ["anio", "Urbano", "Rural"]
    piv.to_csv(OUT / "endes_hijos_area_tiempo.csv", index=False)
    print("\nCEB x area (head):\n", piv.head(3).to_string(index=False))

    # 4. mean age at first birth by education, pooled 2016-2024
    d = q(f"""
        SELECT CAST(educ_nivel AS INT) AS nivel,
          round(sum(edad_primer_hijo*wt)/sum(wt), 2) AS edad_primer_hijo,
          count(*) AS n
        FROM {W}
        WHERE edad BETWEEN 20 AND 49 AND anio BETWEEN 2016 AND 2024
          AND educ_nivel IN (0,1,2,3) AND edad_primer_hijo BETWEEN 10 AND 45
        GROUP BY 1 ORDER BY 1
    """)
    d["nivel_educativo"] = d["nivel"].map(EDUC)
    d = d[["nivel_educativo", "edad_primer_hijo", "n"]]
    d.to_csv(OUT / "endes_edad_primer_hijo_educacion.csv", index=False)
    print("\nEdad 1er hijo x educacion (esperado ~19->~24):\n", d.to_string(index=False))


if __name__ == "__main__":
    main()
