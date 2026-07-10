# Tablas congeladas: procedencia formal

Estas tablas NO se refrescan (el hecho que registran no cambia). Congelar
honesto vence a automatizar falso.

## Censos (censo_*.csv, 6 tablas)
- Fuente: Censos Nacionales INEI 1981, 1993, 2007, 2017 (distribuciones
  distritales del workspace del paper Sendero, copiadas 2026-07-09 a
  ENAHO_ANALYSIS/raw/censos, 188MB).
- Builder reproducible: ENAHO_ANALYSIS/scripts/build_censos_evolucion.py
  (armoniza categorias por censo, agrega nacional y departamental por
  prefijo de ubigeo INEI).
- Validacion: urbanizacion 2017 79.1% vs 79.3% INEI, castellano 83.1% vs
  82.6%, quechua 13.6% vs 13.9% (todas <0.5pp). Analfabetismo publicado con
  universo censado declarado (NO comparable con la cifra oficial 15+).

## Electorales (voto_keiko_*.csv, 2 tablas)
- Fuente: ONPE resultados 2V 2021 (votacion-distrito) y 2V 2026 congelado al
  99.437% de actas (re-pull 2026-06-18, md5 4be400daa4cbab204a8c5177156edf88,
  1,892 distritos 0 vacios, panel comun 1,874).
- Exportacion: shares ponderados sin columnas sensibles, nombres de
  departamento tomados del CSV ONPE.
- OJO ubigeo: la codificacion ONPE NO coincide con la INEI (Lima 14 vs 15).
  Nunca cruzar por codigo entre sistemas — aqui todo cruce departamental fue
  por NOMBRE normalizado.
- Pendiente declarado: re-pull al proclamarse el resultado oficial
  (~mediados de julio 2026) con el scraper gentle documentado en el freeze.
