# Plan: estación y variables climáticas (bloque #16)

## Objetivo

Completar el bloque #16 de [`TODOS.md`](../TODOS.md:143): añadir la estación del año y evaluar variables climáticas históricas con cobertura y valores ausentes documentados.

## Estado actual

[`Partido.matchDate`](../src/football_dataset/FootballClasses.py:32) es una fecha, por lo que la estación puede derivarse de forma determinista sin nuevas fuentes.

## Diseño

1. **Estación determinista:** añadir a [`Partido`](../src/football_dataset/FootballClasses.py:27) el campo `estacion` calculado a partir del mes de `matchDate`. Alternativa más simple: calcularlo en [`DatosTemporada`](../src/football_dataset/DatosTemporada.py:18) sin persistir nueva dependencia.
2. **Variables climáticas históricas:** evaluar una fuente externa (por ejemplo, un dataset público de temperatura/precipitación) y comprobar cobertura por sede y fecha. Solo se incorporarán variables con cobertura suficiente.
3. **Valores ausentes:** representar con `-1` o `NaN` y documentar; registrar incidencias de calidad de severidad *warning* cuando falten.

## Cambios

1. Añadir el campo `estacion` y su exportación en [`dataset_io.py`](../src/football_dataset/dataset_io.py:9).
2. Crear o documentar un adaptador de clima con los mismos principios de inyección del resto del proyecto.
3. Actualizar [`docs/datos.md`](../docs/datos.md:1) con cobertura y unidad de cada variable climática.

## Tests

- Estación correcta para fechas representativas de cada trimestre.
- Ausencia de datos climáticos no rompe la generación.
- El adaptador devuelve estructura tipada y valores ausentes explícitos.

## Criterios de aceptación

- La estación es determinista y documentada.
- Las variables climáticas documentan cobertura, unidad y valores ausentes.
- La suite offline permanece verde.