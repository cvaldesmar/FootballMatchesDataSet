# Plan: persistencia robusta de cachés y esquema (bloque #11)

## Objetivo

Completar el bloque #11 de [`TODOS.md`](../TODOS.md:105): guardado atómico de cachés, validación de versiones y versionado del esquema CSV, con migraciones documentadas.

## Estado actual

- [`MarketHelper`](../src/football_dataset/MarketHelper.py:19) y [`RefereesHelper`](../src/football_dataset/RefereesHelper.py:18) guardan JSON con un campo `version` (`CACHE_VERSION = 2`), pero la escritura no es atómica.
- La carga valida la versión de forma parcial (`payload.get("version")`), pero no hay migradores.
- [`dataset_io.py`](../src/football_dataset/dataset_io.py:9) exporta el CSV sin versión de esquema.

## Cambios

### 1. Escritura atómica compartida

Crear un helper `atomic_write_text(path, content)` o `atomic_json_dump` que:

- escriba en un fichero temporal en el mismo directorio;
- aplique `flush` + `os.fsync`;
- renombre el temporal sobre el destino con `os.replace`.

Reutilizarlo en `MarketHelper.save_values` y `RefereesHelper.save_values`.

### 2. Versionado y migración de cachés

- Mantener `CACHE_VERSION` en cada helper.
- Al cargar, rechazar versiones desconocidas con un `CacheVersionError` descriptivo.
- Definir un registro `MIGRATIONS` de funciones que transformen una versión anterior a la siguiente.
- Si el fichero tiene una versión antigua soportada, aplicar la cadena de migraciones y, al guardar, escribir la versión vigente.

### 3. Esquema CSV versionado

- Añadir una constante `SCHEMA_VERSION` en [`dataset_io.py`](../src/football_dataset/dataset_io.py:1).
- Emitir una cabecera o metadato que permita detectar la versión. Opción más simple: un diccionario `metadata` en una primera fila de comentario o un fichero aparte; la decisión se concreta durante la implementación.
- Registrar la lista de columnas de cada versión como migración documentada.

### 4. Documentación

- Actualizar [`README.md`](../README.md:1) con la sección de cachés, versiones y migraciones.

## Tests

- El guardado y la carga de cachés hacen un *round-trip*.
- Una caché corrupta o de versión desconocida produce error tipado y no rompe silenciosamente.
- Una caché antigua se migra correctamente.
- La escritura atómica no deja ficheros temporales residuales ante fallo simulado.

## Criterios de aceptación

- Las cachés se escriben de forma atómica.
- Las versiones se validan y migran explícitamente.
- El esquema CSV queda versionado y documentado.