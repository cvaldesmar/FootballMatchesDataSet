# Histórico de tareas completadas

Este archivo conserva las tareas y bloques completados que anteriormente formaban parte de [`TODOS.md`](TODOS.md:1). El archivo [`TODOS.md`](TODOS.md:1) contiene únicamente el trabajo pendiente.

## Bloque 1 — Fiabilidad de extracción y calidad de datos

### 1. Capa HTTP robusta

- [x] Crear un cliente HTTP común para todos los scrapers.
- [x] Añadir `timeout` obligatorio.
- [x] Añadir reintentos con backoff para errores transitorios.
- [x] Controlar explícitamente códigos HTTP como 403, 404 y 429.
- [x] Añadir rate limiting y pausas entre peticiones.

**Motivo:** sin una extracción estable no se puede generar ni actualizar el dataset de forma fiable.

### 2. Parsers independientes y validación de estructura

- [x] Separar el parseado de BDFutbol de [`WebScraper.py`](src/football_dataset/WebScraper.py).
- [x] Separar el parseado de Transfermarkt de [`MarketHelper.py`](src/football_dataset/MarketHelper.py) y [`RefereesHelper.py`](src/football_dataset/RefereesHelper.py).
- [x] Validar que las estructuras HTML/JS esperadas existen antes de procesarlas.
- [x] Generar errores descriptivos cuando cambie una fuente externa.

**Motivo:** evita que un cambio silencioso en una web produzca datos incompletos o incorrectos.

### 3. Validación de calidad del dataset

- [x] Detectar partidos duplicados.
- [x] Detectar equipos desconocidos o nombres sin normalizar.
- [x] Validar marcadores, fechas y jornadas.
- [x] Validar el número esperado de equipos y partidos por temporada.
- [x] Generar un informe de calidad antes de guardar el dataset.

**Motivo:** un dataset aparentemente completo puede ser inválido para Machine Learning.

## Bloque 2 — Refactorización que desbloquea pruebas y mantenimiento

### 4. Eliminar el estado global mutable

- [x] Sustituir las variables globales de [`UtilsAndGlobals.py`](src/football_dataset/UtilsAndGlobals.py) por un contexto de ejecución.
- [x] Inyectar configuración, registro de equipos, contador de partidos y helpers.
- [x] Evitar que una ejecución contamine la siguiente.

### 5. Unificar la interfaz de scrapers

- [x] Definir una interfaz común por constructor y atributos de salida para [`WebScraper.py`](src/football_dataset/WebScraper.py) y [`FileScraper.py`](src/football_dataset/FileScraper.py).
- [x] Compartir modelos de salida de equipos y partidos mediante [`models.py`](src/football_dataset/models.py).
- [x] Reducir la lógica duplicada de transformación de datos delegándola en parsers y contexto.

### 6. Crear una suite de tests automatizados

- [x] Probar modelos [`Equipo`](src/football_dataset/FootballClasses.py:8) y [`Partido`](src/football_dataset/FootballClasses.py:27) mediante la suite de regresión.
- [x] Probar normalización y resolución de nombres de equipos.
- [x] Probar parseadores con HTML/CSV fijados como fixtures.
- [x] Probar cálculo de clasificación acumulada y aislamiento de contexto.
- [x] Probar contratos de carga/guardado de cachés JSON mediante helpers inyectados.
- [x] Añadir pruebas de regresión de scraping real para BDFutbol y Transfermarkt, marcadas como integración.

### 7. Configuración y herramientas de proyecto

- [x] Añadir [`pyproject.toml`](pyproject.toml) con configuración de pytest.
- [x] Fijar o acotar versiones en [`requirements.txt`](requirements.txt:1).
- [x] Configurar Ruff como linter y formateador unificado.
- [x] Configurar mypy con tipado estricto progresivo.
- [x] Añadir dependencias de desarrollo a [`requirements.txt`](requirements.txt:1).
- [x] Añadir integración continua en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) con matrices Python 3.11 y 3.12, Ruff, mypy y pytest offline.

**Estado:** Completado.

**Plan de implantación:** [`plan-herramientas-proyecto.md`](plans/dones/plan-herramientas-proyecto.md:1).

### 7.1. Ampliación de cobertura de tests

- [x] Suite base offline e integración separada.
- [x] Añadir tests deterministas del cliente HTTP en [`test_http_client.py`](tests/test_http_client.py).
- [x] Añadir tests de errores y casos negativos de parsers en [`test_parsers_errors.py`](tests/test_parsers_errors.py).
- [x] Añadir tests exhaustivos de validación de calidad en [`test_validation.py`](tests/test_validation.py).
- [x] Añadir tests de exportación CSV y reanudación incremental en [`test_dataset_io.py`](tests/test_dataset_io.py).
- [x] Mantener una suite offline verde de 56 tests unitarios sin dependencias de red.

**Estado:** Completado.

**Plan de implantación:** [`plan-tests-adicionales.md`](plans/dones/plan-tests-adicionales.md:1).

## Bloque 3 — Features útiles para Machine Learning

### 8. Variables históricas previas al partido

- [x] Añadir puntos acumulados antes del partido (`puntosLocal`/`puntosVisitante`).
- [x] Añadir goles a favor y en contra acumulados antes del partido.
- [x] Añadir posición de cada equipo antes del partido (`posicionLocal`/`posicionVisitante`).
- [x] Añadir diferencia de puntos entre local y visitante (`diferenciaPuntos`).
- [x] Congelar la clasificación por jornada para evitar fuga de información intra-jornada.

**Plan de implantación:** [`plan-variables-historicas.md`](plans/dones/plan-variables-historicas.md:1).

### 9. Rachas y enfrentamientos directos sin fuga de información

- [x] Añadir racha reciente de cada equipo (ventana máxima de 5 partidos).
- [x] Añadir resultados de los últimos 5 enfrentamientos entre ambos equipos.
- [x] Garantizar que ninguna variable use información posterior al partido analizado ni de la misma jornada.
- [x] Documentar la ventana temporal de cada variable.

**Plan de implantación:** [`plan-rachas-h2h.md`](plans/dones/plan-rachas-h2h.md:1).

### 10. Contexto competitivo

- [x] Añadir variable `campeonId` con el campeón matemáticamente decidido o `-1`.
- [x] Añadir indicadores `descensoConfirmadoLocal` y `descensoConfirmadoVisitante`.
- [x] Añadir presión competitiva por equipo en escala `0..3`.
- [x] Definir y documentar el tratamiento de empates en clasificación.
- [x] Mantener Europa y ascenso fuera del alcance actual para una futura decisión.

**Plan de implantación:** [`plan-contexto-competitivo.md`](plans/dones/plan-contexto-competitivo.md:1). Implementado.

## Bloque 4 — Persistencia, documentación y operación

### 11. Robustecer cachés y esquema del dataset

- [x] Implementar [`persistence.py`](src/football_dataset/persistence.py) con `atomic_write_text`, `atomic_json_dump` y `load_versioned_json`.
- [x] Definir errores tipados `CacheError`, `CacheVersionError` y `CacheCorruptError`.
- [x] Versionar cachés JSON legibles: versión 3 por equipo/fecha para mercado y versión 2 para árbitros.
- [x] Versionar el esquema CSV con el metadato `# football_dataset_schema=1`.
- [x] Validar estrictamente el metadato y el orden de columnas al reanudar con `append_season`.
- [x] Desacoplar el scraping base del enriquecimiento offline y la gestión de cachés mediante [`enrichment.py`](src/football_dataset/enrichment.py).

**Estado:** Completado.

**Plan de implantación:** [`plan-persistencia-robusta.md`](plans/dones/plan-persistencia-robusta.md:1).

## Bloque 5 — Enriquecimiento opcional

### 14. Distancia de viaje

- [x] Añadir distancia aproximada entre las ciudades de los equipos.
- [x] Documentar coordenadas, método de cálculo y precisión.
- [x] Implementar `migrate_csv_schema()` para evolucionar CSV v1 (también sin metadato) a v2 sin scraping.
- [x] Migrar datasets históricos existentes, preservando valores de mercado y árbitros.
- [x] Publicar la migración CSV de forma atómica y totalmente offline.

**Plan de implantación:** [`plan-distancia-viaje.md`](plans/dones/plan-distancia-viaje.md:1).

### 15. Rivalidades y partidos clásicos

- [x] Definir una lista reproducible de rivalidades clásicas vigentes.
- [x] Añadir flag binaria `rivalidad` (0/1) documentada.
- [x] Garantizar que se exporta al CSV de salida.

**Plan de implantación:** [`plan-rivalidades.md`](plans/dones/plan-rivalidades.md:1). Implementado.

## Resumen histórico

Los bloques #1 al #11 están completados, incluidos #7, #7.1 y #10. También están completados los bloques #14 de distancia de viaje y #15 de rivalidades históricas. La migración evolutiva permite actualizar CSVs v1 existentes a v2 sin red y preservando mercado y árbitros. Todas las variables previas se congelan por jornada para evitar fuga de información.

Existe un dataset base generado en [`data/dataset_historico_1970_2025.csv`](data/dataset_historico_1970_2025.csv), con 43.884 partidos entre 1970 y 2026 y ambas divisiones. El enriquecimiento offline y la gestión de cachés están desacoplados en [`enrichment.py`](src/football_dataset/enrichment.py).

El CSV de salida incluye las variables generadas por los bloques #8, #9, #10 y #15, incluida la flag binaria `rivalidad`. Europa y ascenso quedan documentados como posible ampliación futura.

## Bloque 6 — Preparación para aprendizaje automático

### 18. Calidad del dataset para pronóstico 1X2

- [x] Añadir la variable objetivo explícita `resultado1X2` (1 / X / 2).
- [x] Actualizar el esquema CSV a `SCHEMA_VERSION = 3`.
- [x] Migrar offline los datasets históricos v1/v2 a v3 sin re-scraping.
- [x] Verificar que las 43.884 filas tienen `resultado1X2` coherente con los goles.
- [x] Mantener la suite verde: 64 tests unitarios offline.

**Plan de implantación:** [`plan-calidad-dataset-ml.md`](plans/dones/plan-calidad-dataset-ml.md:1). Implementado.
## Bloque 6 - Analisis y simplificacion de variables para ML (#19)
Implementados ml_features.py, CLI dedicada, flag --build-ml, dataset_ml.csv con 43.884 filas y tests de sintesis.
Plan: plans/dones/plan-analisis-variables-ml.md
## Bloque 19 - Analisis y simplificacion de variables para ML
Implementados 20 campos relativos, features sinteticas, CLI ml_features, flag --build-ml y data/dataset_ml.csv con 43.884 filas.
Plan: plans/dones/plan-analisis-variables-ml.md
