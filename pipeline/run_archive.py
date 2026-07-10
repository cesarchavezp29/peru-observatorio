"""Ejecuta los scripts de pipeline-archive TAL CUAL en un workspace temporal
y verifica sus CSVs contra los committeados — porteo con cero transcripcion.

Mecanica: se arma ws/ con scripts/ (copias del archive + figstyle/enaho_codes
reales del workspace), raw/ (junction de solo lectura a ENAHO_RAW), datasets/
(salida) y figures/ (descartable). Cada script corre con --rebuild y
MPLBACKEND=Agg. La analitica que corre es byte-identica a la archivada: el
runner solo mueve carpetas.

Familias (script -> tablas esperadas) en FAMILIES. Uso:
  ENAHO_RAW=... python pipeline/run_archive.py vivienda_salud --check-against data/datasets
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / "pipeline-archive"
DATASETS = HERE.parent / "data" / "datasets"
HELPERS = ["figstyle.py", "enaho_codes.py", "endes_codes.py", "panel_codes.py",
           "panel_keys.py", "endes_units.py", "panel_io.py", "validate_gasto.py",
           "_epen_dpto_map.py", "_epen_movil_common.py", "dataset_income.py"]

FAMILIES = {
    "vivienda_salud": {
        "fig_vivienda_evolution.py": ["vivienda_servicios_2004_2025.csv"],
        "fig_seguro_salud_evolution.py": ["seguro_salud_2004_2025.csv", "sis_expansion.csv"],
        "fig_calidad_vivienda.py": ["calidad_vivienda_2004_2025.csv"],
        "fig_combustible_cocina.py": ["combustible_cocina_2004_2025.csv"],
        "fig_bienes_difusion.py": ["bienes_durables_difusion_2004_2025.csv"],
        "fig_bienes_durables.py": ["bienes_durables_decil_2025.csv"],
        "fig_salud_cronica_discapacidad.py": ["salud_cronica_discapacidad_2004_2025.csv"],
        "fig_busqueda_atencion_salud_tiempo.py": ["atencion_salud_tiempo.csv"],
        "fig_cuidados_corte_tiempo.py": ["cuidados_personales_tiempo.csv"],
        "fig_jefatura_femenina_pobreza_tiempo.py": ["jefatura_pobreza_tiempo.csv"],
    },
    "gobernabilidad": {
        "fig_confianza_instituciones_tiempo.py": ["confianza_instituciones_tiempo_2007_2025.csv"],
        "fig_confianza_edad_tiempo.py": ["confianza_edad_tiempo_2007_2025.csv"],
        "fig_confianza_educacion_tiempo.py": ["confianza_educacion_tiempo_2007_2025.csv"],
        "fig_confianza_grupos_tiempo.py": ["confianza_grupos_tiempo_2007_2025.csv"],
        "fig_confianza_region_tiempo.py": ["confianza_region_tiempo_2007_2025.csv"],
        "fig_participacion.py": ["participacion_2025.csv"],
        "fig_participacion_evolution.py": ["participacion_organizaciones_2004_2025.csv"],
    },
    "agro": {
        "fig_agro_comercializacion_evolution.py": ["agro_comercializacion_2011_2025.csv"],
        "fig_agro_mercado.py": ["agro_mercado_2025.csv"],
        "fig_agro_productos.py": ["agro_top_cultivos_2025.csv", "agro_top_especies_2025.csv"],
        "fig_agro_volumen_valor.py": ["agro_volumen_valor_2025.csv"],
    },
    "eea_rest": {
        "build_eea_activos.py": ["eea_activos_sector.csv"],
        "build_eea_brecha_genero.py": ["eea_brecha_genero_sector.csv"],
        "build_eea_concentracion.py": ["eea_concentracion_industria.csv", "eea_concentracion_sector.csv"],
        "build_eea_demografia.py": ["eea_demografia_sector.csv"],
        "build_eea_remuneraciones.py": ["eea_remuneraciones_sector.csv"],
        "build_eea_ventas_va.py": ["eea_ventas_va_sector.csv"],
        "build_eea_epen_cruce.py": ["eea_epen_cruce_sector.csv"],
    },
    "demografia_consumo": {
        "fig_transicion_demografica.py": ["transicion_demografica_2004_2025.csv"],
        "fig_migracion_interna_tiempo.py": ["migracion_interna_tiempo.csv"],
        "dataset_migracion_od.py": ["migracion_od_departamento.csv"],
        "dataset_sector_flujo.py": ["empleo_sector_flujo_2007_2011.csv"],
        "fig_poblacion_indigena.py": ["poblacion_indigena_2004_2025.csv"],
        "fig_brecha_ingreso_etnico_tiempo.py": ["brecha_ingreso_etnico_tiempo.csv"],
        "build_consumo_evolution.py": ["budget_composition_2004_2025.csv"],
        "fig_engel_elasticidades.py": ["engel_elasticidades_2025.csv"],
        "fig_engel_elasticidad_tiempo.py": ["engel_elasticidad_tiempo_2004_2025.csv"],
    },
    "empleo_brechas": {
        "fig_brecha_salarial_sexo.py": ["brecha_salarial_sexo_2004_2025.csv"],
        "fig_brecha_salarial_hora_tiempo.py": ["brecha_salarial_hora_tiempo_2004_2025.csv"],
        "fig_brecha_salarial_edad_tiempo.py": ["brecha_salarial_edad_tiempo_2004_2025.csv"],
        "fig_brecha_salarial_region_tiempo.py": ["brecha_salarial_region_tiempo_2004_2025.csv"],
        "fig_brecha_salarial_urbano_tiempo.py": ["brecha_salarial_urbano_tiempo_2004_2025.csv"],
        "fig_brecha_salarial_formal_tiempo.py": ["brecha_salarial_formal_tiempo_2007_2025.csv"],
        "fig_brecha_salarial_grupos.py": ["brecha_salarial_grupos_tiempo_2004_2025.csv"],
        "fig_brecha_salarial_sector.py": ["brecha_salarial_sector_2025.csv"],
        "fig_trabajo.py": ["estructura_empleo_2004_2025.csv"],
        "fig_pea_sexo.py": ["pea_sexo_2004_2025.csv"],
        "fig_neet_juvenil_tiempo.py": ["neet_juvenil_tiempo_2004_2025.csv"],
        "fig_subempleo_horas.py": ["subempleo_horas_2004_2025.csv"],
        "fig_empleo_sectores.py": ["empleo_sectores_2004_2025.csv"],
        "fig_empleo_agricola_evolution.py": ["empleo_agricola_2004_2025.csv"],
        "fig_trabajo_adolescente_escuela_tiempo.py": ["trabajo_adolescente_tiempo.csv"],
        "fig_discapacidad_empleo_tiempo.py": ["discapacidad_empleo_tiempo.csv"],
        "fig_penalidad_maternidad_tiempo.py": ["penalidad_maternidad_tiempo.csv"],
    },
}


def setup_ws(raw: Path) -> Path:
    ws = Path(tempfile.mkdtemp(prefix="archive_ws_"))
    (ws / "scripts").mkdir()
    (ws / "datasets").mkdir()
    (ws / "figures").mkdir()
    # junction de solo lectura al raw (Windows: mklink /J, sin admin)
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(ws / "raw"), str(raw)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL junction:", r.stderr.strip())
        sys.exit(1)
    src_scripts = Path(r"D:\ENAHO_ANALYSIS\scripts")
    for h in HELPERS:
        if (src_scripts / h).exists():
            shutil.copy(src_scripts / h, ws / "scripts" / h)
    return ws


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("familia", choices=list(FAMILIES))
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("ENAHO_RAW", "peru_raw/enaho"))
    ws = setup_ws(raw)
    env = dict(os.environ, MPLBACKEND="Agg")
    plan = FAMILIES[a.familia]
    produced, failed = [], []
    for script, tables in plan.items():
        src = ARCHIVE / script
        if not src.exists():
            print(f"[skip] {script}: no esta en el archive")
            continue
        shutil.copy(src, ws / "scripts" / script)
        print(f"[run ] {script}")
        r = subprocess.run([sys.executable, str(Path("scripts") / script), "--rebuild"],
                           cwd=ws, env=env,
                           capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            print(f"  FAIL rc={r.returncode}: {r.stderr.strip().splitlines()[-1][:160] if r.stderr.strip() else r.stdout[-160:]}")
            failed.append(script)
            continue
        for t in tables:
            if (ws / "datasets" / t).exists():
                produced.append(t)
            else:
                print(f"  ! {script} no produjo {t}")
                failed.append(t)

    if a.check_against:
        refdir = Path(a.check_against)
        bad = 0
        for t in produced:
            ref = pd.read_csv(refdir / t)
            new = pd.read_csv(ws / "datasets" / t)
            ok = list(ref.columns) == list(new.columns) and len(ref) == len(new)
            if ok:
                for c in ref.columns:
                    rv = pd.to_numeric(ref[c], errors="coerce")
                    nv = pd.to_numeric(new[c], errors="coerce")
                    if rv.notna().any():
                        d = (rv - nv).abs().max()
                        if pd.notna(d) and d > 1e-3:
                            print(f"  FAIL {t} col {c}: max diff {d}")
                            ok = False
                            break
                    elif not ref[c].astype(str).equals(new[c].astype(str)):
                        print(f"  FAIL {t} col {c}: texto")
                        ok = False
                        break
            else:
                print(f"  FAIL forma {t}: ref {ref.shape} vs new {new.shape}")
            bad += 0 if ok else 1
        print(f"\n[{a.familia}] {len(produced)} tablas producidas, {bad} con diferencias, "
              f"{len(failed)} fallos de ejecucion")
        sys.exit(1 if (bad or failed) else 0)


if __name__ == "__main__":
    main()
