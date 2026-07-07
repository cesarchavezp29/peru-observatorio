# ENAHO — Validación externa y gotchas de construcción

> Regla del proyecto (Carlos): **ningún número se publica sin validarlo contra una
> fuente externa de INEI**, y **todo hallazgo sobre cómo está construido el ENAHO se
> anota aquí**. Esta es la bitácora.

## 1. Validación de cada figura contra cifras oficiales INEI

| Figura / indicador (mío) | Mi valor | INEI oficial | Fuente | Veredicto |
|---|---|---|---|---|
| Agua red pública **dentro** vivienda 2024 (`p110==1`) | 82.5% | **83.5%** | ENAHO 2024 (INEI, capítulo Servicios) | ✅ ±1 pp |
| Teléfono celular 2024 (`p1142==1`) | 95.1% | **~95%** | ENAHO 2024 TIC | ✅ exacto |
| Alumbrado eléctrico 2024 (`p1121==1`) | 96.1% | **92.6%** (red pública) | ENAHO 2024 | ⚠️ definición: el mío es *cualquier fuente* (incluye panel/generador); INEI publica *red pública*. Etiquetado como tal. |
| Empleo agrícola 2024 (CIIU rev4 A, `p506r4` 111-322, `ocu500==1`) | 23.0% | **24.2%** (sector primario: agric.+pesca+**minería**) | INEI EPEN / Informe Empleo 1T-2024 | ✅ el mío excluye minería → algo menor, consistente |
| Pobreza monetaria 2025 | 25.7% | 25.7% | INEI nota de prensa pobreza | ✅ (validación previa) |
| Internet hogares 2024 (`p1144==1`, crudo) | 91.6% | **58.4%** | INEI Informe TIC 4T-2024 | ❌ **NO valida** — ver §3 |

Marcadores `x` en las figuras = cifra oficial INEI, dibujada junto a la serie como
validación visible.

## 2. Gotchas de construcción (cómo está hecho el ENAHO)

- **Las columnas `gru*hd1/hd2` de Sumaria NO suman a `gashog2d`.** Suman ~2-5% del
  gasto total: son sólo las formas SECUNDARIAS de adquisición (pago en especie,
  donación, autoconsumo). El grueso *comprado* se guarda con otra nomenclatura.
  → No reconstruir la canasta de 8 grupos sumando `gru*`; usar la metodología INEI
  o los módulos 07-18 agregados con su columna de valor. La compuerta de validación
  (`suma/gashog2d ≈ 1.0`) atrapó el error antes de graficar. **No se publicó canasta.**
- **El `data_label` interno del `.dta` viene vacío** en los archivos INEI. La identidad
  real del módulo se lee de `variable_labels()` (la etiqueta de la variable `pNNNn`
  nombra la sección). Por eso la numeración 08-18/77/78/84 hubo que verificarla del
  dato, no asumirla (varias estaban mal en la primera pasada — corregido).
- **Formato Stata viejo (v110) en M01 2005-2009**: pandas 3.0 no lo lee (soporta
  111/113/114/115/117/118/119, no 110). Fallback con `pyreadstat.read_dta`. Helper
  `read_dta()` en los scripts de figura. Sin esto se pierden 5 años en silencio.
- **`factor07` colisiona** al unir un módulo que ya lo trae con Sumaria (queda
  `factor07_x/_y`). Traer el peso de una sola fuente.

## 3. El caso internet (`p1144`) — por qué se excluyó

INEI publica **58.4% de hogares con internet (4T-2024)**, coherente con mi serie
**hasta 2022** (`p1144` ≈ 55% en 2022). Pero el `p1144` **crudo salta a ~90% desde
2023**. Decomposición con la batería nueva `p114b1/b2/b3` (fija/móvil-postpago/
móvil-prepago), 2025:

- `p1144==1` (cualquier acceso) = **91.1%**
- de ésos, **fija** (`p114b1`) ≈ 31% → población con internet **fijo ≈ 30%**, plano 2023-2025
- **móvil** ≈ 95% de los hogares con internet

La pregunta cambió de concepto en 2023 (de *conexión del hogar* a *acceso por
cualquier medio, incluido el dato móvil de cada miembro*) manteniendo el mismo nombre
y etiqueta — **ruptura silenciosa**. El 90% **no** es la cifra que INEI titula como
"hogares con internet" (58.4%). Por eso el indicador **se excluye** del gráfico de
modernización hasta reconciliar la serie con la definición oficial INEI.

## 3b. Transferencias monetarias (Juntos / Pensión 65) — M37 cap. 700A

Serie 2013-2025 (`fig_transferencias_cobertura_tiempo`). Dos trampas resueltas:

- **Renumeración de códigos** `p710_NN`: JUNTOS = `p710_03` en 2013 y `p710_04`
  desde 2014 (Wawa Wasi se partió en diurno+acompañamiento y corrió a Juntos un
  lugar); PENSIÓN 65 = `p710_05` todos los años. Verificado leyendo el
  **CED-01-700A** y los value-labels de `p712` en el subarchivo `700b` de CADA año
  (extraídos a `raw/_dicc/m37/`).
- **Cambio de formato 2021-2024**: el módulo pasa a formato LARGO (una fila por
  persona×programa, `p712` con value-labels 4=Juntos/5=Pensión 65) y **no trae
  filas de "no recibió"** → el denominador se ancla en Sumaria (todos los hogares),
  no en el propio módulo. La serie no muestra salto en la transición ancho↔largo
  (2020 → 2021 → 2025 continua), lo que valida la elección de denominador.

**Recall**: la pgta. 710 pregunta "en los últimos 3 AÑOS" → la cobertura mide
"recibió en algún momento de los últimos 3 años", por lo que los niveles superan la
afiliación puntual. Validación de tendencia (no impresa en la figura, sólo QA):
Pensión 65 (creado oct-2011) sube de 3.8% a 9.5% de hogares, coherente con la rampa
MIDIS (~250k usuarios 2013 → ~830k 2024, ≈8% de hogares en 2024 vs mi 8.7%); Juntos
estancado ~9-11% (afiliación puntual ~700k hogares ≈ 6.8%, menor que el 9% por la
ventana de 3 años). Direcciones y órdenes de magnitud validan.

## 3c. Cuidado personal — M78 (gastos, cap. 606D)

Series 2004-2025 (`fig_cuidados_servicios_tiempo`, `fig_cuidados_corte_tiempo`). M78 es
un submódulo de GASTO (no de cuidados/trabajo de cuidado): producto `p606n`, códigos
**1-11 verificados estables** leyendo value-labels (2013/2025) y CED-01-606D (estable
2004 vs 2025). BIENES = 1-9 (jabón, champú, pasta, desodorante, toallas, colonia,
labial, art. bebé, otros); SERVICIOS = 10 corte de cabello + 11 otros servicios. Valor
de adquisición por ítem = `i606f` (compra) + `i606g` (valor estimado de lo no comprado),
imputado/deflactado/anualizado por INEI.

Métrica = **participación intra-anual** (share dentro del año → el deflactor se cancela,
no se comparan niveles en soles entre años; evita la trampa de subconteo de los módulos-
ítem vs grupos oficiales ya anotada). No hay número INEI publicado equivalente (consumo-
composición es descriptivo ENAHO-only); la figura cita sólo ENAHO. Hallazgos: servicios
suben de ~11% (2004) a 19% (2025) del gasto de cuidado personal, con caída COVID-2020 a
13.5% y recuperación que **supera** el pre-pandemia hacia 2023. Corte de cabello pagado
(margen extensivo, % hogares/mes): 43%→61% (2019), se hunde a 44% en 2020 y **no** vuelve
al pico (≈50% en 2025) — cicatriz de hábito/presupuesto. Faltan 2005, 2007-2010, 2012
(módulo no recolectado, igual que el resto de gasto 07-18).

## 3d. Cobertura de seguro vs acceso a la atención — M04 (Salud)

Series 2007-2025 (`fig_busqueda_atencion_salud_tiempo`, `fig_razones_no_atencion_tiempo`).
Universo = personas con problema de salud en 4 semanas (p4021-p4024). BUSCÓ ATENCIÓN
FORMAL = acudió a establecimiento/profesional (p4031-p4039 + p40311 domicilio del
profesional); EXCLUYE farmacia (p40310), curandero, otro y "no buscó" (p40314).
Códigos 402/403 y la lista de razones 409 **verificados idénticos 2007 vs 2025** leyendo
el **CED-01A-400** (extraído a `raw/_dicc/m04/`).

Hallazgo (honesto, va contra una narrativa optimista): el SIS subió el aseguramiento de
15% a 66%, pero la **consulta profesional entre enfermos sigue en ~1/3** y no subió
(32.6% en 2025 vs 30.9% en 2007; caída COVID-2020 a 21.5%, recuperada). Gradiente por
seguro persiste (2025: EsSalud 41% > SIS 31% > sin seguro 12%), pero la tasa SIS **cayó**
de 47% (2007) a 31% — efecto composición: el SIS pasó de un grupo pequeño/seleccionado a
la población pobre general. Mecanismo (fig razones): "no tuvo dinero" se desploma de 22%
a 4% (el SIS quitó el gasto de bolsillo), y lo que queda es no-financiero: "no era grave"
sube de 35% a 48% (mayoría) y la automedicación ~24%. Lectura: cobertura ≠ acceso; el
seguro resolvió el precio, no la distancia/espera/percepción de gravedad.

Definición vs INEI: mi tasa formal (~32%) EXCLUYE farmacia; INEI suele reportar "buscó
atención" más alto si incluye botica. Orden de magnitud y "no era grave" como razón
dominante consistentes con los boletines de salud INEI. Sólo QA, no impreso en figura.

## 3e. Migración interna reciente — M04 (Salud), p401f

Serie 2016-2025 (`fig_migracion_interna_tiempo`). `p401f` "Hace 5 años, vivía en este
distrito?" (1=Sí, 2=No=migrante, **3=Aún no había nacido** → excluido del denominador).
Disponible **sólo 2016-2025** (ausente antes). Migrante reciente = p401f==2; edad =
año - año de nacimiento (p400a3). Ponderado factor07.

Hallazgo: migración fuertemente joven (18-29 ≈ 8-11%, doble-triple del 50+ ≈ 3%),
urbano > rural, gradiente estable. Caída COVID-2020 (mínimo 5.2% global) y rebote
2021-22 (7.2%), tendencia de fondo a la baja (urbanización que madura). Consistente con
el patrón de migración INEI/Censo (concentración en adultos jóvenes, dirección rural→
urbano). Magnitud de migración reciente de 5 años en el orden esperado.

CAVEAT: mide cambio de DISTRITO en 5 años (incluye mudanzas intra-metropolitanas entre
distritos vecinos; no toda migración). Distritos creados después de 2015 pueden inflar
levemente. 2020 ENAHO parcialmente telefónica. QA, no impreso en figura.

## 3f. Trabajo adolescente — MULTI-MÓDULO M05 × M03 × M34

Series 2004-2025 (`fig_trabajo_adolescente_pobreza_tiempo`,
`fig_trabajo_adolescente_escuela_tiempo`). CRUCE de tres módulos, anclado en M05 (persona
14-17): **M05** (empleo) `ocu500` ocupado=1, `p208a` edad, `fac500a` peso; **M03**
(educación) `p306` matriculado + `p307` asiste (estudia = ambos ==1), por llave-persona
`conglome+vivienda+hogar+codperso`; **M34** (Sumaria) `pobreza in {1,2}`, por llave-hogar.
Merge LEFT 100% emparejado para los adolescentes. Peso = `fac500a` (M05).

VERIFICACIÓN DE CÓDIGOS (verify_codes.py, requisito antes de la serie): `ocu500`
(1=ocupado), `p306`/`p307` (1=sí/2=no), `pobreza` (1=extremo/2=pobre) **idénticos los 22
años** — sin drift. M05 arranca a los 14 → es trabajo ADOLESCENTE (14-17), no infantil
(5-13, fuera del módulo); declarado en figura y fuente.

Hallazgos (honestos, incluyen el que va contra la narrativa de progreso): (1) ocupación
14-17 cae 39.4%→20.6% (casi a la mitad), consistente con la baja del trabajo infantil que
reporta INEI/MTPE. (2) La brecha por pobreza **desaparece**: 2004 pobre 44.8% vs no pobre
29.6% (+15 pp); 2025 20.7% vs 20.5% (≈0) — dejó de ser fenómeno de pobreza. (3) De los que
trabajan, la fracción que además estudia sube 40%→58% (el trabajo se vuelve compatible con
la escuela). (4) Descomposición 4-vías: "solo estudia" 41%→59%, "solo trabaja" 24%→9%,
"estudia y trabaja" 16%→12%, **"ni estudia ni trabaja" PLANO ~20%** (no mejoró pese al
crecimiento — núcleo adolescente al margen, coherente con el NEET 15-24 ~22-25% ya
documentado). Sólo ENAHO en la figura; validación de dirección, no nivel externo impreso.

## 3g. Penalidad de la maternidad — MULTI-MÓDULO M02 × M05

Serie 2004-2025 (`fig_penalidad_maternidad_tiempo`). CRUCE M02 (composición del hogar) ×
M05 (empleo), anclado en M02 persona: sexo `p207` (1=hombre/2=mujer), edad `p208a`;
`has_child_u6` = el hogar tiene ≥1 miembro de 0-5 años (llave-hogar). M05 `ocu500`
ocupado=1, peso `fac500a`, merge por llave-persona. Universo 25-45.

VERIFICACIÓN: `p207` (1=hombre/2=mujer, estándar INEI; algunos años sin value-labels en
el .dta pero códigos idénticos), `ocu500` (1=ocupado), `p208a` — estables. CAVEAT: "niño
en el hogar" es proxy de hogar-con-crianza; para 25-45 casi siempre es hijo propio, pero
hogares extensos pueden incluir hermano/nieto menor. No usa parentesco `p203`.

Hallazgo (honesto, contra-narrativa de progreso): un niño pequeño BAJA el empleo femenino
(2025: con-niño 63.7% vs sin-niño 76.9% ≈ -13 pp) y lo SUBE en el hombre (con-niño 94.4%
vs sin-niño 88.0% = efecto proveedor). La penalidad femenina **NO se redujo: creció de
-8.5 pp (2004) a -13.2 pp (2025)** — porque suben las mujeres SIN niños (74→77%) mientras
las madres se estancan/bajan (66→64%). No hay penalidad masculina (signo positivo todo el
periodo). Validación de patrón (penalidad de maternidad + prima de paternidad) consistente
con la literatura de género; sólo ENAHO en la figura, dirección no nivel externo impreso.
Complementa la suite de brecha salarial de género (figures/07_empleo).

## 3h. Estudio de evento del child penalty — MULTI-MÓDULO M02 × M05

`fig_evento_maternidad_empleo`. Perfil tipo Kleven et al. (2019): empleo de 25-45 por EDAD
DEL HIJO MENOR del hogar (tiempo de evento, 0 = año de nacimiento), mujeres vs hombres,
contra la referencia de sin-hijo-0-17. Mismas variables/módulos y verificación que §3g.
Años 2016-2025 agrupados (celdas robustas), peso fac500a. Edad del hijo menor =
`min(edad)` entre miembros 0-17 del hogar.

LÍMITE METODOLÓGICO (declarado en la figura): ENAHO es CORTE TRANSVERSAL → esto es un
pseudo-panel SINTÉTICO (perfil por edad del hijo menor), **no** un event study de panel
intra-persona; no hay periodo pre-nacimiento observado para la misma mujer, así que la línea
"sin hijos" hace de contrafactual de nivel. La selección por fecundidad (quién tiene hijos)
puede sesgar niveles; el perfil de recuperación es robusto al patrón conocido.

Resultado: en el nacimiento (t=0) la madre cae a 53.5% vs 76.1% de la mujer sin hijos
(≈ -23 pp de penalidad), y se recupera gradualmente hasta ~77% cuando el hijo llega a edad
escolar (t≈12). El padre NO cae: salta a 94% en t=0 (vs 84% sin hijos = prima de
paternidad/selección) y se mantiene. Forma consistente con la literatura de child penalty.
Complementa la serie temporal de la penalidad (§3g): el evento muestra el MECANISMO (caída
al nacer + recuperación por edad del hijo) detrás del promedio.

## 3i. Discapacidad y exclusión laboral — MULTI-MÓDULO M04 × M05 × M34

`fig_discapacidad_empleo_tiempo` (2016-2025). DISCAPACIDAD = cualquiera de `p401h1-6`==1
(limitación permanente moverse/ver/hablar/oír/entender/relacionarse, set corto tipo
Washington Group; M04 Salud, disponible 2016+). Cruce con M05 (`ocu500`, `p208a`,
`fac500a`) por llave-persona y M34 (`pobreza`) por llave-hogar. Universo 25-59 (aísla edad
de trabajar; la prevalencia sube fuerte con la edad → la de toda la población es mayor por
los adultos mayores). VERIFICACIÓN: `p401h1-6` (1=sí/2=no) y `ocu500` estables 2016-2025.

Hallazgo (exclusión que empeora): la ocupación de 25-59 con discapacidad cae de 59% (2016)
a ~53% (2025) mientras la de sin-discapacidad se mantiene ~83% → brecha ~25→30 pp que se
ENSANCHA. Además viven en hogares más pobres (DIS ~30% vs noDIS ~23% en 2025; brecha que
crece con el COVID). Prevalencia 25-59 ~2.7→3.7% (sube por envejecimiento + mejor reporte;
la población total ~5-6% por adultos mayores, ya en `fig_salud_cronica_discapacidad`).
Dirección consistente con INEI/Censo 2017 (menor inserción laboral de personas con
discapacidad). Sólo ENAHO en la figura.

## 3j. Jefatura femenina y pobreza — MULTI-MÓDULO M02 × M34

`fig_jefatura_femenina_pobreza_tiempo` + `fig_jefatura_femenina_share_tiempo` (2004-2025).
Jefe = miembro M02 con `p203`==1; jefa = ese miembro es mujer (`p207`==2). Merge con M34
(`pobreza`, `factor07`) por llave-hogar. Peso = factor07 (hogar).

VERIFICACIÓN DE CÓDIGOS: `p203` código **1 = "jefe/jefa" estable** todos los años. El
`[DRIFT]` que marca `verify_codes.py` es sólo el *wording* del código 2 (esposo/esposa →
"esposo(a)/compañero(a)") — no afecta la identificación del jefe. `p207` (1=hombre/2=mujer)
estándar. Documentado como **falsa alarma de label** (la jefatura es comparable).

Hallazgo (honesto, contra-intuitivo, debunk): (1) la jefatura femenina **sube fuerte** de
21.8% (2004) a 38.7% (2025) — cambio estructural. (2) Los hogares con jefa son **siempre
algo MENOS pobres** que los de jefe hombre (2004: 44.3% vs 52.9%; 2025: 18.3% vs 21.3%) →
la "feminización de la pobreza" NO aplica a Perú. CAVEAT importante (no sobreinterpretar como
empoderamiento): la pobreza es per cápita y los hogares con jefa suelen ser más chicos
(viudez, hogares unipersonales, parejas con varón migrante que envía remesas); la menor
pobreza refleja composición/tamaño, no necesariamente mayor ingreso. Edad de la jefa ~54
(similar al jefe en 2025). Sólo ENAHO en la figura; patrón consistente con la literatura de
hogares peruanos.

## 3k. Movilidad educativa intergeneracional — MULTI-MÓDULO M02 × M03

`fig_movilidad_educativa_tiempo` (2004-2025). Asistencia a un centro educativo de jóvenes
17-21 (edad de educación superior) según la educación del JEFE del hogar. Jefe = M02
`p203`==1 → su `codperso`; su educación = `p301a` de su fila en M03, difundida al hogar;
asistencia del joven = `p306`==1 y `p307`==1. Niveles del jefe: ≤primaria (`p301a`≤4),
secundaria (5-6), superior (7-11); código 12 (básica especial, desde 2017) excluido de los
tres grupos (marginal). Peso factor07.

VERIFICACIÓN: `p203` (1=jefe/jefa), `p301a` (1-11 estable, 12 added 2017), `p306`/`p307`
(1=sí/2=no), `p208a` — estables. Diseño de DOS niveles de cruce: M02 identifica al jefe →
su educación se trae de M03 (misma persona, otra fila) → se difunde al hogar → se cruza con
la asistencia del joven (otra persona del hogar). Es la lógica "padre→hijo" dentro del hogar
(proxy: jefe del hogar como progenitor; para 17-21 corresidentes suele ser el padre/madre).

Hallazgo (honesto, persistencia más que movilidad): a los 17-21, asistir es sobre todo
educación superior. El gradiente por educación del jefe es FUERTE y PERSISTE: jefe-superior
~55% vs jefe-≤primaria ~35% en 2025 (brecha ~20 pp), prácticamente IGUAL que en 2004
(+21.6 pp). El acceso subió para todos (los hijos de jefes con primaria pasaron de 25% a
35%), pero la ventaja por origen familiar casi no se movió → la educación superior se
"hereda". Contrasta con la asistencia 12-16 (escolaridad básica), cuya brecha por origen SÍ
se cerró (de +14 a +7 pp) — el piso se igualó, el techo no. Sólo ENAHO; patrón consistente
con la baja movilidad educativa documentada para Perú/AL.

## 3l. Brecha étnica de ingresos: educación vs paga — MULTI-MÓDULO M05 × M03

`fig_brecha_ingreso_etnico_tiempo` (2007-2025). Ingreso laboral de asalariados de lengua
indígena como % del de castellano-hablantes, CRUDO y DENTRO de educación superior. M05
(`i524a1` ingreso anual dependiente, `p507` 3/4 asalariado, `p301a`, `p208a`, `fac500a`,
`ocu500`, 25-59) × M03 (`p300a` lengua: indígena = 1 quechua/2 aimara/3 otra nativa; no
indígena = 4 castellano). Mediana ponderada, ratio intra-anual (deflactor se cancela).

VERIFICACIÓN: `p300a` indígena **1-3 estable** (el code 5 inglés cae tras 2013 y 8/9
cambian en 2018, pero 1-3 no se tocan — ver tabla de breaks del README); `p507` (3/4),
`ocu500`, `p301a` estables. CAVEAT honesto: mediana cruda sin control de horas/experiencia/
región/ocupación; "dentro de superior" es control grueso; los indígenas que llegan a
superior pueden estar positivamente seleccionados.

Hallazgo: la brecha étnica de ingresos es sobre todo de EDUCACIÓN/oportunidad, no de paga.
El ratio CRUDO sube de 68% (2007) a ~92% (2025) — la brecha se cierra a la mitad. Y DENTRO
de educación superior ya había **paridad (~100%)** todo el periodo (0.99 en 2007, ~1.0 en
2025). Es decir: a igual educación, el ingreso indígena ≈ no indígena; el grueso de la
brecha cruda viene de menor acceso educativo (y ubicación/ocupación). CONTRASTA fuerte con
la brecha de GÉNERO, que SÍ persiste dentro de educación (universitarias ganan ~0.85; ver
suite de género en figures/07_empleo). Sólo ENAHO en la figura.

## 4. Otras rupturas de comparabilidad ya anotadas

- **`trust_share` (mód. 85)**: "No sabe" (5) como dato perdido infla la confianza de
  los menos educados (dejan en blanco lo que no conocen) → U espuria en educación.
  Tratado como *no confía* sobre las 21 instituciones → gradiente **monótono**
  (8.3% sin nivel → 20.5% postgrado; nacional 14.2%). *Pendiente: validar el 14.2%
  contra el Informe de Gobernabilidad de INEI.*
- **Rama de actividad** `p506` migra CIIU rev3 → rev4 entre años.
- **SIS `p4195`**: el código de "no" cambia (0 en 2004, 2 en 2025) — usar `==1`.

## Fuentes externas

- ENAHO 2024 servicios básicos — INEI / Gestión: <https://gestion.pe/economia/mas-de-73-de-la-poblacion-rural-no-tiene-acceso-a-red-de-alcantarillado-inei-servicios-basicos-noticia/>
- INEI publicación Servicios (cap.01): <https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib2027/cap01.pdf>
- Informe Técnico Empleo Nacional 1T-2024: <https://www.inei.gob.pe/media/MenuRecursivo/boletines/02-informe-tecnico-empleo-nacional-primer-trimestre-2024.pdf>
- Informe Técnico TIC 4T-2024 (58.4% hogares con internet): <https://www.inei.gob.pe/media/MenuRecursivo/boletines/boletin_tic_iit24.pdf>
- INEI nota: 58.9% hogares con internet 1T-2025: <https://www.gob.pe/institucion/inei/noticias/1195629-inei-58-9-de-los-hogares-del-pais-tiene-acceso-a-internet-en-el-primer-trimestre-de-2025>
