# Pipeline reproducible

Ver docs/PIPELINE_SPEC.md. W1 en curso: manifest.csv, build_sumaria.py, workflow verify.

## Verificacion del panel (local, no CI)
Los crudos del panel que build_panel_familias.py consume pesan ~89GB (modulos de
persona multi-ola), inviables como release asset o en runners de 45 min. El port
quedo verificado valor por valor contra lo committeado (60/60 tablas, 2026-07-09)
y cualquiera puede repetirlo: descargar releases con perudata.panel y correr
PANEL_RAW=... python pipeline/build_panel_familias.py --check-against data/datasets
