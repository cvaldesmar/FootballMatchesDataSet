# Plan: datos avanzados de partido (bloque #17)

## Objetivo

Completar el bloque #17 de [`TODOS.md`](../TODOS.md:151): evaluar fuentes de lesiones, sanciones, posesión, disparos, alineaciones y tácticas, incorporando solo lo que tenga cobertura y calidad suficientes.

## Estado actual

El proyecto obtiene resultados (BDFutbol), valores de mercado y árbitros (Transfermarkt). No existen datos avanzados de partido.

## Enfoque: evaluación antes que incorporación

Este bloque es prioritariamente de análisis. Antes de añadir campos se debe:

1. Identificar fuentes candidatas y su cobertura histórica.
2. Documentar licencia, frecuencia y riesgo de scraping.
3. Definir un esquema reproducible para cada variable.
4. Validar la cobertura contra temporadas objetivo; descartar variables con demasiados huecos.

## Variables candidatas

- **Lesiones y sanciones:** nombre del jugador, tipo, duración y fecha; dependen de una fuente fiable por temporada.
- **Posesión, disparos, alineaciones y cambios tácticos:** requieren proveedores de estadísticas; evaluar disponibilidad histórica para Primera y Segunda.

## Cambios

1. Crear [`docs/evaluacion-datos-avanzados.md`](../docs/evaluacion-datos-avanzados.md:1) con la matriz de fuentes: cobertura, calidad, licencia y decisión.
2. Para cada variable aceptada, seguir el patrón del proyecto: modelo en [`models.py`](../src/football_dataset/models.py:1), adaptador/parser propio, integración en [`DatosTemporada`](../src/football_dataset/DatosTemporada.py:18) y columna en [`dataset_io.py`](../src/football_dataset/dataset_io.py:9).
3. Omitir variables con cobertura insuficiente, dejándolo documentado.

## Criterios de aceptación

- Existe una matriz documentada de fuentes y decisiones.
- Solo se incorporan variables con cobertura y calidad suficientes.
- Cada variable nueva queda tipada, documentada y testeada.
- La suite offline permanece verde.