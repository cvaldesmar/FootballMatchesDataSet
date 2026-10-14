# Plan: comando de diagnóstico (bloque #12)

## Objetivo

Completar el bloque #12 de [`TODOS.md`](../TODOS.md:113): añadir un comando operativo que evalúe rápidamente la salud de fuentes, cachés, temporadas y entradas/salidas.

## Estado actual

- [`Main.py`](../src/football_dataset/Main.py:177) es el único punto de entrada. Existe `--list-seasons`, pero no una comprobación integral de estado.
- El cliente HTTP y los parsers ya están desacoplados y pueden reutilizarse para probar conectividad.

## Diseño

Añadir un subcomando `--check` o `--diagnose` que genere un informe por logging y código de salida:

1. **Conectividad:** una petición ligera a BDFutbol y a Transfermarkt con timeout corto; reportar `OK`, `HTTP xxx`, error o skip.
2. **Cachés:** existencia de `market_values.json` y `referees.json`, versión detectada y compatibilidad con la vigente.
3. **Temporadas:** listar temporadas disponibles y confirmar que se conocen la última y el rango histórico.
4. **Entrada/salida:** al usar `--source file`, validar que el CSV de entrada existe y cumple las columnas obligatorias.
5. **Validaciones rápidas:** ejecutar una validación parcial o un chequeo de esquema sin persistir.

## Cambios

1. Crear [`diagnostics.py`](../src/football_dataset/diagnostics.py:1) con funciones puras y testeables que devuelvan un resultado estructurado.
2. Añadir `--check` en [`Main.py`](../src/football_dataset/Main.py:44) y enlazarlo con el informe.
3. Reutilizar [`HttpClient`](../src/football_dataset/http_client.py:30) y [`DatasetValidator`](../src/football_dataset/validation.py:38).
4. Evaluar si exponer el resultado como texto o JSON (`--check-format json`).

## Tests

- Cada comprobación devuelve una estructura `DiagnosticResult` con estado y mensaje.
- El comando devuelve código `0` si todo está bien y distinto de cero ante error.
- La ausencia de cachés no aborta si la comprobación está desactivada o es informativa.

## Criterios de aceptación

- `python -m src.football_dataset --check` muestra un informe legible.
- El código de salida refleja el estado global.
- Las comprobaciones no exigen datos reales para poder ejecutarse en pruebas.