# Plan: contexto competitivo (bloque #10)

## Objetivo

Completar el bloque #10 de [`TODOS.md`](../TODOS.md:96): añadir a cada partido indicadores de campeón decidido, descenso confirmado y presión competitiva, documentando el tratamiento de empates.

## Estado actual

- [`DatosTemporada`](../src/football_dataset/DatosTemporada.py:18) ya congela la clasificación por jornada (`_freeze_standings`), por lo que existe el snapshot previo necesario para calcular posición y distancias.
- [`Partido`](../src/football_dataset/FootballClasses.py:27) aún no expone columnas de contexto competitivo.
- El desempate de posición usa puntos, diferencia de goles y goles a favor, pero no está documentado formalmente.

## Decisión final y variables

Alcance acordado: título, descenso y presión. Se omiten por ahora los puestos de Europa y ascenso.

Campos nuevos en [`Partido`](../src/football_dataset/FootballClasses.py:27):

- `campeonId: int`: identificador global del equipo matemáticamente campeón al inicio de la jornada, o `-1` si todavía no hay campeón decidido. Es idéntico para todos los partidos de la misma jornada.
- `descensoConfirmadoLocal: int`: `1` si el local está matemáticamente descendido al inicio de la jornada; `0` en caso contrario.
- `descensoConfirmadoVisitante: int`: idem para el visitante.
- `presionLocal: int`: nivel de presión competitiva del local, en escala `0..3`.
- `presionVisitante: int`: idem para el visitante.

Escala de presión `0..3`:

- `0`: sin presión (mitad de tabla sin objetivo vivo, objetivo ya decidido, o equipo ya descendido).
- `1`: presión leve (objetivo matemáticamente vivo pero con margen holgado).
- `2`: presión alta (lucha directa por el título o por evitar el descenso).
- `3`: presión máxima (tramo final con margen muy ajustado).

`DESCENSOS_POR_DIVISION` se define en [`Const.py`](../src/football_dataset/Const.py:1) como `{1: 3, 2: 4}` por defecto y se documenta como aproximación histórica configurable.

## Regla contra fuga de información

Todas las variables se calculan desde el snapshot congelado de la jornada (`_freeze_standings`). Ninguna usa el resultado del partido actual ni de partidos posteriores.

## Tratamiento de empates

Se usa el orden ya presente en [`_freeze_standings()`](../src/football_dataset/DatosTemporada.py:76): puntos, diferencia de goles, goles a favor y, como último criterio estable, el `idGlobalClub`.

## Algoritmo determinista

Para cada jornada `j`, con `standings = _freeze_standings()` y `n = len(standings)`:

1. `descensos = DESCENSOS_POR_DIVISION[division]`; `last_safe_pos = max(1, n - descensos)`.
2. Ordenar por posición: `leader` es el de posición 1 y `safe_pts` son los puntos del equipo en `last_safe_pos`.
3. `remaining = numJornadas - j + 1`; `max_gain = remaining * puntosPorVictoria`.
4. `campeonId = leader` si para todo equipo distinto del líder `pts + max_gain < leader_pts`; si no, `-1`.
5. Por cada equipo:
   - `descenso = (pos > last_safe_pos) and (pts + max_gain < safe_pts)`.
   - Presión de título:
     - `0` si hay campeón decidido o `pts + max_gain < leader_pts`.
     - si `gap = leader_pts - pts`: `3` si `remaining <= 4 and gap <= 2 * puntosPorVictoria`; `2` si `gap <= 2 * puntosPorVictoria`; `1` en otro caso.
   - Presión de descenso:
     - en zona `pos > last_safe_pos`: `0` si ya descendido, `3` si `remaining <= 4`, `2` en otro caso.
     - cerca de la zona `pos <= last_safe_pos` con `gap = safe_pts - pts`: `2` si `remaining <= 4 and gap <= 2 * puntosPorVictoria`; `1` si `gap <= 2 * puntosPorVictoria`; `0` en otro caso.
   - `presion = max(titulo, descenso)`.

El `campeonId` es único por jornada y se copia en todos los partidos de esa jornada.

## Cambios

1. Ampliar [`Partido`](../src/football_dataset/FootballClasses.py:27) con los cinco campos nuevos.
2. Añadir `DESCENSOS_POR_DIVISION` en [`Const.py`](../src/football_dataset/Const.py:1).
3. Implementar `_compute_competitive_context()` en [`DatosTemporada.py`](../src/football_dataset/DatosTemporada.py:19), consumiendo el snapshot congelado y devolviendo campeón y, por equipo, descenso y presión.
4. En [`loadMatches()`](../src/football_dataset/DatosTemporada.py:55), calcular el contexto de la jornada antes de construir sus partidos y pasar a [`addMatch()`](../src/football_dataset/DatosTemporada.py:97) los valores de local/visitante.
5. Añadir las columnas a [`dataset_io.py`](../src/football_dataset/dataset_io.py:9).
6. Documentar en [`README.md`](../README.md:1) y [`TODOS.md`](../TODOS.md:96).

## Tests

- Sin campeón decidido al inicio de temporada (`campeonId == -1`).
- Campeón decidido cuando la ventaja es insalvable con los puntos restantes.
- Descenso matemático confirmado cuando `pts + max_gain < safe_pts`.
- Presión `0` para mitad de tabla sin objetivos.
- Presión `3` en tramo final con margen ajustado por título o descenso.
- Ausencia de fuga: el resultado del partido actual no altera sus propias variables.
- Igualdad de `campeonId` para todos los partidos de una jornada.

## Estado

Implementado y validado con la suite offline. El alcance final incluye campeón matemático, descenso confirmado y presión competitiva `0..3`; Europa y ascenso quedan fuera del alcance actual.

## Criterios de aceptación

- Las variables son reproducibles con la clasificación previa.
- El tratamiento de empates está documentado.
- La suite offline permanece verde.