# pipeline-archive: los productores actuales, tal cual

Cada CSV analitico del sitio nace de uno de estos scripts. Se publican SIN
modificar desde el workspace original (D:\ENAHO_ANALYSIS\scripts): rutas de
Windows, imports locales (enaho_codes, figstyle, panel_io) y todo. Feo pero
honesto: un esceptico puede leer hoy la logica exacta que produjo cada numero,
mientras el porteo a pipeline/ (con perudata y verificacion valor por valor)
avanza incrementalmente segun docs/PIPELINE_SPEC.md.

ARCHIVE_MAP.csv mapea tabla -> script productor actual. Ya portados y
verificados (viven en pipeline/, no aqui): official_poverty_replication
(build_sumaria.py, gate de CI), las 60 familias del panel
(build_panel_familias.py, 60/60 valor por valor), informalidad_reconstruida
(build_empleo.py, 22x7 valor por valor). Congelados con procedencia: censos y
electorales (ver manifest).
