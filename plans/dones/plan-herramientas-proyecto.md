# Plan: herramientas de proyecto (bloque #7)

## Objetivo

Cerrar el bloque #7 de [`TODOS.md`](../TODOS.md:75): dotar al proyecto de linting, formateo, type checking e integración continua reproducibles.

## Estado actual

- [`pyproject.toml`](../pyproject.toml:1) ya contiene configuración de pytest con marcadores `unit`/`integration`.
- No existe configuración de antes o formateo.
- No existe type checking; el código usa *type hints* pero no se verifica.
- No existe pipeline de CI.

## Decisiones de herramientas

- **Linting y formateo:** [`ruff`](https://docs.astral.sh/ruff/) como linter y formateador único (`ruff check` y `ruff format`).
- **Type checking:** [`mypy`](https://mypy-lang.org/) con modo estricto progresivo.
- **CI:** GitHub Actions con tres etapas: lint, type check y tests (offline; los de integración quedan excluidos por defecto).

## Cambios

### 1. [`pyproject.toml`](../pyproject.toml:1)

Añadir secciones `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]` y `[tool.mypy]`:

- `line-length = 100`.
- Selector de reglas base `["E", "F", "I", "UP", "B"]`.
- `target-version = "py311"` o la versión mínima soportada.
- `strict = true` en mypy (de forma progresiva; permitir ignorar errores existentes si es necesario).

### 2. [`requirements.txt`](../requirements.txt:1)

Añadir `ruff` y `mypy` (o bien separarlos en un fichero de desarrollo). Documentar su instalación en [`README.md`](../README.md:1).

### 3. CI

Crear [`.github/workflows/ci.yml`](../.github/workflows/ci.yml:1) con:

- `ruff check .`
- `ruff format --check .`
- `mypy src`
- `pytest -q`

## Tests

No hay tests funcionales nuevos: las comprobaciones son estáticas. Se añade un smoke test de que el paquete importa.

## Criterios de aceptación

- `ruff check .` no reporta errores.
- `ruff format --check .` no reporta diferencias.
- `mypy src` termina sin errores (o con un umbral documentado de errores tolerados).
- El workflow de CI ejecuta lint, type check y tests offline.