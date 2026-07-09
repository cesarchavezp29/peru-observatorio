# Fase 1 spec: pipeline reproducible (recibido 2026-07-09)

## Paso 0 (antes de portar nada): pipeline/manifest.csv
Fila por tabla: table -> producing script -> source (survey, modules, years) ->
cadencia (monthly/annual/frozen) -> validation target. Es checklist de porteo,
lo que CI itera, y de donde build_db.py lee pipeline_script + last_built para
inyectar al catalogo y a los pies de grafico autocitables.

## Mapa: 220 tablas = ~14 scripts
- 62 tablas = 3-4 scripts de familias panel parametrizados por ventana (perudata panel.load_long).
- ENAHO por modulo: sumaria(34: pobreza replica, Ginis, percentiles, GIC, income real, budget ~12t,
  validate.poverty ya es 80% del primero), empleo(05: informalidad, 8 brechas, subempleo, PEA, adolescente),
  vivienda/TIC(01/04: servicios, durables, seguro, SIS), gobernabilidad(85: trust, participacion),
  agro, transferencias(37, trampa p710). Cada gotcha de la bitacora = assertion ejecutable
  (gate gru* canasta, exclusion p1144, regla factor07).
- Wrappers: ENDES(6, endes.load), EEA(11, eea.load), EPEN(Lima via catalogo verificado), WDI script.
- NO-perudata: BCRP/IPC via API BCRP (fetcher standalone). Censos + ONPE = FROZEN:
  pipeline/static/ con nota de procedencia (URL, fecha, reconciliacion ubigeo). Congelar honesto > automatizar falso.

## CI: 3 workflows
1. verify (cada PR): rebuild duckdb -> boot API -> smoke endpoints -> perudata poverty gate.
   FALLA si la pobreza se desvia de INEI en cualquier monto. Badge en README. El movimiento insignia.
2. monthly-epen (cron): EPEN+BCRP -> regenerar ~29 CSVs empleo -> ABRIR PR (no commit directo)
   con resumen de celdas cambiadas — INEI revisa series, un humano mira el diff.
3. annual-enaho (manual dispatch, disparado por el issue del watcher): solo el ano nuevo,
   append mode, gate completo, PR. Igual ENDES/EEA.
Mecanica: cache de peru_raw en Actions keyed year+module (vintages historicos no cambian),
.duckdb fuera de git, perudata gana retry-with-backoff para INEI (correr 3am Lima).

## Orden por fin de semana
W1: manifest + script sumaria + workflow verify con gate y badge + perudata a PyPI.
W2: familias panel (caen 62). W3: empleo+vivienda+gobernabilidad. W4: EPEN+BCRP+cron mensual.
W5: ENDES/EEA/WDI. W6: agro, transferencias, static/, last_built en pies de grafico.
Lo no portado tras W6: pipeline-archive/ tal cual con README honesto, manifest lo marca pending.
Extra: snapshot Zenodo para DOI (citable antes de Fall 2027).

## Regla de parada
Si JOLE o el paper de automatizacion necesitan el fin de semana, el sitio lo pierde, siempre.

## Regla de porteo (no negociable)
NO refactorizar la logica analitica al portar: mover el script, envolverlo en sus
assertions de validacion, confirmar que el CSV de salida coincide valor por valor
con el committeado, commit. Mejorar la economia de una tabla y migrar su plomeria
en el mismo commit = un fin de semana bisecando que cambio movio un numero.
Portar primero, mejorar despues — el workflow verify protege las mejoras cuando exista.
