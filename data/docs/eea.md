# EEA — Metodología y trampas (cómo NO equivocarse en estimaciones futuras)

Guía de uso de los microdatos de la **Encuesta Económica Anual (EEA)** del INEI en este toolkit
(`D:\ENAHO_ANALYSIS`, datos en `raw/eea_inei/`, descarga con `scripts/eea_download.py`). Resume
lo aprendido construyendo las 8 figuras EEA + el cruce con EPEN, **con auditoría hecha** (sin
doble conteo, sin explosión de merge). Léelo antes de tocar la EEA otra vez.

---

## 0. Lo que SÍ está auditado y limpio (2026-06-27)

- **No hay doble conteo empresa/establecimiento.** En todos los capítulos financieros
  `FlagEstablecimiento == 1` (Empresa) en el 100% de las filas — el dato viene **consolidado a
  nivel de empresa**, no por establecimiento. Sumar/promediar es seguro.
- **IRUC es único** dentro de cada Clave (una fila por empresa por Clave). Los merges por IRUC
  **no explotan** (verificado: productividad 6,320 → 6,320 filas, sin pérdida ni cartesiano).
- **Un solo c00 por módulo** (no hay archivos duplicados que dupliquen ventas).

---

## 1. Reglas de oro (las que evitan el 90% de los errores)

1. **Año: EEA `YYYY` = año fiscal `YYYY-1`.** La EEA 2024 trae datos de **2023** (archivos
   `a2023_*`). Etiqueta tus figuras con el año fiscal, no el de la encuesta.
2. **Las medidas derivadas existen SOLO para empresas grandes (formato `F2`).** Valor agregado,
   producción, balance, productividad, participación del trabajo, brecha de género, activos:
   **todo sale del formulario detallado F2**. Las **medianas (M)** y **micro (N)** NO tienen
   Estado de Producción ni Balance. Nunca reportes VA/activos "por tamaño F2/M/N" — no existe
   para M/N. La dimensión tamaño se hace por **nº de trabajadores DENTRO de F2**.
3. **El RUC está anonimizado** (id secuencial de 6 díg, no el RUC real de 11). Seguro de usar y
   difundir agregados. Es la llave de merge entre capítulos (`IRUC`, primera columna, con BOM —
   renómbrala a `iruc`).
4. **Usa el archivo de capítulo ESPECÍFICO, nunca un heurístico.** Para el VA, lee
   `*_c03_1.csv` directo. Un heurístico tipo "el archivo con más filas Clave 88" agarra
   `c08E`/`c09E` (personal) que tienen una Clave 88 espuria = 0. Mismo cuidado con todos.
5. **Las etiquetas de Clave NO están en el `.sav`.** Para mapear Clave→concepto, abre el
   `Diccionario_Variables_*.pdf` de ESE formulario (uno por sector) e imprime la tabla del
   capítulo en crudo: el concepto termina con el número de Clave. (Tampoco hay etiquetas de
   `CodSector` ni `CIIU` en el .sav.)
6. **Los números de capítulo VARÍAN por formulario.** El mapa de abajo es de Comercio; en
   Manufactura y otros, el balance o la producción pueden estar en otro `cNN`. Localiza por
   CONTENIDO (qué Claves tiene), no por número.

---

## 2. Mapa de capítulos (referencia Comercio `s04_fF2`; verifica por sector)

| Archivo | Capítulo | Qué saco | Clave / columna |
|---|---|---|---|
| `*_c00_1.csv` | Carátula / frame | **Ventas** (frame), CIIU, ubigeo, FACTOR_EXP | `VENTAS2023` (col., 1 fila/empresa, Clave 0) |
| `*_c02_1.csv` | Balance General | **Total Activo**, **PP&E**, depreciación | Clave 42 = Total Activo · 28 = PP&E bruto · 29 = (−)Deprec. (`dato1`=2023, `dato2`=2022) |
| `*_c03_1.csv` | Estado de Producción | **Producción (VBP)**, **Valor Agregado** | Clave 38 = Producción Total · 87 = Consumo · **88 = VALOR AGREGADO** (`dato1`) |
| `*_c09_1.csv` | Gastos de Personal | **Compensación**, **remuneraciones**, **por sexo** | Clave 01 = TOTAL comp · 02 = Remuneraciones · `dato3`=Perm.Hombre `dato4`=Perm.Mujer `dato6`=Event.Hombre `dato7`=Event.Mujer |
| `*_c10_1.csv` | Personal Ocupado | **Trabajadores**, **por sexo** | Clave 08 = Total personal · `dato1`=Total `dato2`=Hombre `dato3`=Mujer |

Definiciones derivadas (todas ponderadas por `FACTOR_EXP`, F2):
- **Productividad** = VA(c03 Clave 88) / trabajadores(c10 Clave 08). Merge por IRUC (seguro).
- **Participación del trabajo** = compensación(c09 Clave 01) / VA. Agregado 2023 = **45.5%**.
- **Salario medio** = remuneraciones(c09 Clave 02) / trabajadores(c10 Clave 08). Mensual = /12.
- **Brecha género** = salario_H / salario_M, con comp por sexo (c09 d3+d6 vs d4+d7) y personal
  por sexo (c10 d2 vs d3).
- **Inversión (PROXY)** = PP&E bruto 2023 − 2022 (c02 Clave 28 `dato1`−`dato2`). **NO es la FBKF
  exacta** (neta de retiros, afectada por revaluaciones). El capítulo de movimiento de activo
  fijo con las ADICIONES brutas es ambiguo (uno parece producción, otro depreciación 395xx); no
  se reconstruyó para no publicar un número dudoso.

---

## 3. Anclas de validación (si esto no cuadra, hay un error)

- **El Balance cuadra:** Total Activo (c02 Clave 42) = Total Pasivo+Patrimonio (Clave 84). En
  Comercio S/341B = S/341B. Si no cuadran, leíste mal el Clave.
- **VA total F2 ≈ 1/3 del PBI** (S/342B en 2023, PBI ~S/1,000B). VA/Producción ≈ 46%.
- **Participación del trabajo ≈ 45%** (rango sectorial 11–67%). Espejo de la intensidad de
  capital y la productividad (utilities: alta productividad, bajo peso laboral, alta intensidad).
- **Las 20 empresas mayores tienen peso ≈ 1** (censo, máx 1.5) → por eso los CR4/CR8 son válidos
  (los líderes están todos capturados). Si una "gran empresa" tuviera peso alto, sospecha.

---

## 4. Trampas concretas encontradas (y su estado)

| Trampa | Impacto | Estado |
|---|---|---|
| **Construcción: ventas = 2022, no 2023** (su formulario solo trae `VENTAS2021`/`VENTAS2022`) | ventas/VA de construcción mezclan años (ventas 2022, VA 2023) | **Documentado**; afecta solo a construcción en ventas y concentración (menor). No corregible (no hay columna 2023). |
| **CIIU rev.3 (≤2007) vs rev.4 (≥2008)** | aplicar un solo mapeo cruza Comercio rev3 (div. 50-52) con Transportes rev4 → saltos falsos (52%→6%) | **Resuelto**: `build_eea_demografia.py` detecta versión por año y mapea distinto. |
| **Niveles de empresas NO comparables en el tiempo** | factor de expansión solo desde 2012 (nulo en 2021); universo cambia (2024 sumó micro) | **Resuelto**: la demografía reporta **composición** (participación), no niveles, y solo 2012-2024 ponderado. |
| **VA Clave 88 con heurístico** | agarra c08E/c09E con Clave 88 = 0 | **Resuelto**: se usa `*_c03_1.csv` específico. |
| **Cruce EEA↔EPEN "Otros servicios"** | EPEN incluye sector público (Adm. pública, educación/salud estatal); la EEA NO. Sube el ingreso EPEN de "Otros servicios" y **subestima** el premio de ese sector | **Documentado**; el resto de sectores (comercio, manufactura, agro, etc.) son comparables. |
| **Hidrocarburos sin Estado de Producción estándar** | VA = 0 si se usa c03 | **Documentado**: se excluye de VA/productividad; Minería/Hidroc. queda fuera del cruce. |

---

## 5. Cruce con EPEN (lado trabajador)

- **Fuente EPEN nacional por sector**: EPEN Dpto, códigos **790/874/935/1001 = 2022/23/24/25**
  (`c309_cod` rama CIIU, `ingtotp` ingreso, `informal_p`, `fac300_anual`). Para 2023 usa **874**.
- **Alineación de sector**: macro por **división CIIU de 2 dígitos** en AMBOS lados. EPEN
  `c309_cod` es de 3-4 díg → `zfill(4)[:2]` para la división. Usa la MISMA función `macro()` que
  la EEA (ojo: telecom CIIU 58-63 va en "Transp./Comunic." en ambos, no en "Otros servicios").
- **Interpretación**: EEA = salario de la gran empresa formal; EPEN = ingreso de TODOS los
  trabajadores (incl. informales, independientes, micro). El cociente = premio formal/duralidad.

---

## 6. Checklist antes de declarar una estimación EEA terminada

1. ¿Es F2-only? Si la medida es VA/activos/productividad/remuneración → sí, dilo.
2. ¿Año fiscal correcto? (encuesta − 1).
3. ¿Leí el Clave del **archivo de capítulo específico** (no heurístico)?
4. ¿Verifiqué `FlagEstablecimiento==1` e IRUC único antes de sumar/mergear? (en chapters nuevos).
5. ¿Cuadra con un ancla? (balance, VA~1/3 PBI, labor share ~45%, pesos de grandes ≈1).
6. ¿CIIU rev.3 vs rev.4 si es serie temporal?
7. ¿Abrí el PNG y validé la magnitud contra el orden esperado?
