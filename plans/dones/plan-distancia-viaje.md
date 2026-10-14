# Plan: distancia de viaje (bloque #14)

## Objetivo

Completar el bloque #14 de [`TODOS.md`](../TODOS.md:127): añadir la distancia aproximada entre las ciudades de los equipos, con coordenadas y método documentados.

## Estado actual

**Completado.** El registro geográfico, el cálculo offline y la columna `distanciaKm` ya están integrados. [`migrate_csv_schema()`](../src/football_dataset/enrichment.py:47) acepta CSV v1 con o sin metadato, conserva las columnas de enriquecimiento y publica esquema v2 atómicamente, sin volver a scrapear. La CLI se ejecuta con `python -m src.football_dataset.enrichment --input ... --migrate-in-place`.

## Diseño

1. Añadir en [`Const.py`](../src/football_dataset/Const.py:1) un diccionario `CITY_COORDINATES` con `(latitud, longitud)` por cada sede histórica de los equipos normalizados.
2. Implementar un helper puro en [`UtilsAndGlobals.py`](../src/football_dataset/UtilsAndGlobals.py:1) que calcule la distancia Haversine en kilómetros.
3. Añadir a [`Partido`](../src/football_dataset/FootballClasses.py:27) la columna `distanciaKm` (entero o flotante, según decisión de implementación).
4. Calcular la distancia en [`DatosTemporada.addMatch()`](../src/football_dataset/DatosTemporada.py:80) usando los nombres normalizados y el snapshot de jornada (el valor es invariante al resultado).
5. Exponer la columna en [`dataset_io.py`](../src/football_dataset/dataset_io.py:9).
6. Migrar CSVs existentes con [`migrate_csv_schema()`](../src/football_dataset/enrichment.py:47) o mediante la CLI, conservando mercado y árbitros.
7. Escribir metadato, cabecera y filas mediante [`atomic_write_text()`](../src/football_dataset/persistence.py:25).
8. Validar la migración con tests unitarios y conteo de filas/valores numéricos en los datasets históricos.

## Tratamiento de ausencias

Si una sede no tiene coordenadas (`None`), el campo se marca con convención `-1` (como otros valores ausentes) y se registra una incidencia de calidad de severidad *warning*, sin interrumpir el proceso.

## Tests

- Distancia entre dos ciudades conocidas con valor esperado aproximado.
- Sede ausente produce `-1` sin fallo.
- Par simétrico: la distancia es la misma para local/visitante invertidos.

## Criterios de aceptación

- [x] Las coordenadas y el método de cálculo están documentados.
- [x] Los valores ausentes se representan de forma consistente como `-1`.
- [x] La migración v1→v2 es offline, atómica y preserva campos enriquecidos.
- [x] Los dos datasets históricos contienen 43.884 filas con `distanciaKm` numérica.
- [x] La suite offline y Ruff permanecen verdes.