# Plan de campaña del Observatorio (crítica estratégica 2026-07-09)

Cuatro fases con dependencias. Portfolio, no el evento principal: si JOLE o el
paper de automatización necesitan el fin de semana, el sitio lo pierde, siempre.

## Fase 1 — La columna: reproducible y vivo (críticas 1+2)
- pipeline/ en el repo: un script por familia de CSV, importando perudata,
  empezando por las ~15 tablas que citan las páginas editoriales.
- perudata como capa de datos (publicarlo a PyPI a la vez).
- GitHub Actions cron mensual: pipeline EPEN -> rebuild duckdb -> commit -> autodeploy.
- Contrato visible: last_built + pipeline_script por tabla en el catálogo y el pie de cada gráfico.
- Alternativa honesta: pipeline-archive/ con los scripts Windows tal cual + README que lo admite.

## Fase 2 — El marco: audiencia y línea editorial (7 -> 3+4)
- Audiencia primaria: periodistas. Investigadores via perudata, ciudadanos via juegos.
- Tesis de portada: "El país que cambió todo menos el trabajo" (informalidad ~70%
  dos décadas mientras consumo/salud/educación se transformaron). Las series
  incómodas con la misma prominencia que las lisonjeras (estancamiento post-2016, cicatriz COVID).
- Componente "¿es mucho?": benchmark Chile/Colombia/LatAm + rango departamental
  bajo cada KPI nacional (las tablas WDI ya existen).
- El Explorer de 214 tablas se degrada a "Datos" en el footer: deja de fingir ser el producto.
- Prerender + ECharts code-split van con esta reestructura.

## Fase 3 — La conciencia: lenguaje y exposición (5+6) [dos noches]
- Pasada por essays.js, scrollies y content.js: todo verbo causal colgado de una
  correlación transversal se degrada a asociación, o lleva "esto es una asociación,
  no un efecto causal" explícito — la honestidad epistémica visible como diferenciador.
- QuienVoto simétrico: "el mapa de la grieta", ambos polos descritos. [HECHO 2026-07-09]

## Fase 4 — El foso: módulo de movilidad (8) [timebox: UNA página]
- Movilidad educativa intergeneracional desde educación de los padres en ENAHO
  (matrices de transición por cohorte y región), Mincer por cohorte, link al DiD
  de salario mínimo. Deliberadamente descriptivo. Material de aplicación PhD.

## Encaje de lo anterior
BrowserRouter+fallback [HECHO], datos.qhawarina.pe + footers autocitables con Fase 1,
keepalive [HECHO], sitemap [HECHO].
