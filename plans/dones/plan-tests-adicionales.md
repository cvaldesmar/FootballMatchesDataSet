# Plan: ampliación de cobertura de tests

## Objetivo

Ampliar la confianza del proyecto más allá de la suite base actual, protegiendo las capas HTTP, parsers, validación, exportación incremental y variables históricas antes de ejecutar generaciones grandes del dataset.

## Estado actual

La suite offline se ejecuta con `python -m pytest -q` y cubre modelos, contexto, parsers principales, clasificación, cachés JSON, variables históricas, contexto competitivo, rivalidades y guardado incremental. Los tests de scraping real están separados mediante el marcador `integration`.

## Fase 1 — Cliente HTTP

Añadir tests deterministas con sesiones falsas para:

- timeout y `ConnectionError` con reintentos hasta agotar el máximo;
- backoff exponencial y respeto de `Retry-After` en respuestas `429`/`5xx`;
- errores tipados para `403`, `404`, `429` y respuestas inesperadas;
- cabecera `User-Agent`, timeout y parámetros enviados a la sesión;
- rate limiting entre peticiones usando reloj y `sleep` inyectados.

## Fase 2 — Parsers y contratos de fuentes

Crear fixtures mínimas y casos negativos para:

- BDFutbol sin `resultats`, sin equipos, sin partidos y JSON incompleto;
- fechas, IDs y marcadores inválidos en BDFutbol;
- CSV sin columnas obligatorias, filas de otra temporada, fechas inválidas y `golDiff` incoherente;
- Transfermarkt sin selector, tabla, enlaces o valores;
- árbitros con tabla ausente, fechas inválidas y filas incompletas.

Cada caso debe producir [`ParserError`](../src/football_dataset/parsers/errors.py:1) con mensaje accionable.

## Fase 3 — Validación de calidad

Cubrir [`DatasetValidator`](../src/football_dataset/validation.py:38) con:

- duplicados por jornada/local/visitante;
- equipos no incluidos en `known_team_ids`;
- jornadas no positivas y fuera de rango;
- fechas no ISO o fuera de temporada;
- goles negativos y `golDiff` inconsistente;
- conteos inesperados de equipos/partidos;
- warnings frente a errores y comportamiento de `max_errors`.

## Fase 4 — Exportación y reanudación

Añadir pruebas de [`dataset_io.py`](../src/football_dataset/dataset_io.py:1) para:

- cabecera completa y orden estable de [`HEADERS`](../src/football_dataset/dataset_io.py:9);
- serialización de todas las variables nuevas, incluidos campeón, descenso, presión y rivalidad;
- `append_season()` sin duplicar la cabecera;
- varias temporadas concatenadas sin mezclar filas;
- archivo conservado con temporadas ya escritas si una temporada posterior falla;
- compatibilidad de [`save_all_seasons()`](../src/football_dataset/dataset_io.py:44).

## Fase 5 — Variables históricas y fuga de información

Añadir tests de regresión y propiedades:

- todos los partidos de una jornada comparten snapshot de clasificación, forma, H2H y contexto competitivo;
- un resultado nunca influye en sus propias variables;
- ventanas de forma/H2H nunca superan cinco partidos;
- H2H es simétrico respecto a local/visitante;
- posiciones, puntos y diferencia de puntos son coherentes;
- `campeonId`, descenso y presión sólo usan información previa;
- rivalidad es binaria y simétrica.

## Fase 6 — Regresiones de integración controladas

Mantener tests pequeños contra fuentes reales, con rate limiting y `@pytest.mark.integration`:

- una temporada conocida de Primera en BDFutbol;
- una temporada conocida de Segunda;
- una comprobación opcional de Transfermarkt;
- exclusión por defecto en CI y ejecución explícita bajo demanda.

## Organización propuesta

- Mantener [`tests/test_core.py`](../tests/test_core.py:1) para contratos básicos.
- Mantener [`tests/test_refactor_closure.py`](../tests/test_refactor_closure.py:1) para regresiones funcionales integradas.
- Crear [`tests/test_http_client.py`](../tests/test_http_client.py:1), [`tests/test_parsers_errors.py`](../tests/test_parsers_errors.py:1), [`tests/test_validation.py`](../tests/test_validation.py:1) y [`tests/test_dataset_io.py`](../tests/test_dataset_io.py:1) cuando cada fase se implemente.
- Centralizar dobles y fixtures compartidos en [`tests/conftest.py`](../tests/conftest.py:1) y [`tests/fixtures/`](../tests/fixtures).

## Criterios de aceptación

- La suite offline cubre todos los contratos críticos y no requiere red.
- Los fallos de fuentes externas producen errores tipados y mensajes verificables.
- El guardado incremental queda protegido frente a duplicación de cabecera y pérdida de temporadas anteriores.
- Las variables históricas tienen tests explícitos contra fuga de información.
- Los tests de integración siguen excluidos por defecto.
- `python -m pytest -q` permanece verde.