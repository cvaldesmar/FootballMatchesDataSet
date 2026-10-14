# Plan: variables históricas previas al partido (bloque #8)

## Objetivo

Completar el bloque #8 de [`TODOS.md`](../TODOS.md:69) sin introducir fuga de información. Añadir posición previa al partido, diferencia de puntos y garantizar que todas las variables previas se congelan al inicio de cada jornada.

## Estado actual (diagnóstico)

En [`DatosTemporada.addMatch()`](src/football_dataset/DatosTemporada.py:53) el [`Partido`](src/football_dataset/FootballClasses.py:27) se construye leyendo `self.clasificacion`, `self.golesafavor` y `self.golesencontra` **antes** de llamar a [`updateClassification()`](src/football_dataset/DatosTemporada.py:93). Por tanto ya quedan capturados sin fuga:

- `puntosLocal`, `puntosVisitante`
- `golesafavorlocal`, `golesencontralocal`
- `golesafavorvisitante`, `golesencontravisitante`

Falta:

1. `posicionLocal` y `posicionVisitante`: posición en la tabla antes del partido.
2. `diferenciaPuntos`: diferencia de puntos entre local y visitante.
3. Congelar la clasificación por jornada: hoy `updateClassification()` muta la tabla partido a partido, de modo que el último partido de una jornada observa resultados previos de la misma jornada (fuga de información intra-jornada).

## Diseño de datos

Ampliar [`Partido`](src/football_dataset/FootballClasses.py:27) con tres campos nuevos:

- `posicionLocal: int`
- `posicionVisitante: int`
- `diferenciaPuntos: int`

Los nombres siguen el estilo en español y sin tildes ya presente en el modelo.

El orden de la tabla para calcular la posición usa, en orden descendente de prioridad:

1. Puntos acumulados.
2. Diferencia de goles acumulada (`golesafavor - golesencontra`).
3. Goles a favor acumulados.

Se documenta que este desempate es provisional; el tratamiento definitivo de empates queda pendiente en el bloque #10 de [`TODOS.md`](../TODOS.md:96).

## Cambios necesarios

### 1. [`FootballClasses.py`](src/football_dataset/FootballClasses.py:27)

- Añadir `posicionLocal`, `posicionVisitante` y `diferenciaPuntos` al dataclass con coerción a `int` en `__post_init__`.
- Añadir los campos a `__str__`.

### 2. [`DatosTemporada.py`](src/football_dataset/DatosTemporada.py:48)

- Cambiar el procesamiento de `loadMatches()`: agrupar los partidos por jornada.
- Antes de cada jornada, calcular una clasificación congelada (`_freeze_standings()`) que devuelva, para cada equipo, su posición según los tres criterios anteriores, usando la tabla acumulada al inicio de esa jornada.
- En `addMatch()`, leer posición y diferencia de puntos desde la clasificación congelada de la jornada, no desde el estado partido a partido.
- Aplicar `updateClassification()` para todos los partidos de la jornada solo después de construir todos los partidos de esa misma jornada.

### 3. [`dataset_io.py`](src/football_dataset/dataset_io.py:9)

- Añadir `posicionLocal`, `posicionVisitante` y `diferenciaPuntos` a `HEADERS`.

### 4. Tests

- Añadir test que verifique que dos partidos de la misma jornada comparten la misma clasificación congelada (sin fuga intra-jornada).
- Añadir test de que `diferenciaPuntos` es coherente con `puntosLocal - puntosVisitante`.
- Añadir test de que las posiciones se asignan por puntos, luego diferencia de goles y luego goles a favor.

## Criterios de aceptación

- `posicionLocal` y `posicionVisitante` son enteros positivos y representan la posición previa al partido.
- `diferenciaPuntos` coincide con `puntosLocal - puntosVisitante`.
- Todos los partidos de una misma jornada leen la misma tabla congelada.
- La suite offline (`python -m pytest -q`) queda verde.
- El CSV exportado incluye las tres columnas nuevas.