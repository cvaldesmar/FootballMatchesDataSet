# Plan: rachas y enfrentamientos directos sin fuga de información (bloque #9)

## Objetivo

Completar el bloque #9 de [`TODOS.md`](../TODOS.md:76) incorporando variables históricas útiles para Machine Learning sin usar el resultado del partido analizado ni ningún partido posterior.

## Variables propuestas

### Rachas recientes

Para cada partido:

- `rachaLocal`: balance de los últimos 5 partidos del equipo local antes del partido.
- `rachaVisitante`: balance de los últimos 5 partidos del equipo visitante antes del partido.
- `formaLocal`: secuencia compacta de los últimos 5 resultados (`W`, `D`, `L`), del más antiguo al más reciente.
- `formaVisitante`: equivalente para el visitante.

El balance numérico se calculará con el sistema de puntos de la temporada (`3/1/0` desde 1995 y `2/1/0` antes), para mantener coherencia histórica. Los equipos con menos de 5 partidos usarán únicamente el historial disponible; no se rellenará con información futura.

### Enfrentamientos directos

Para cada partido:

- `h2hLocalWins`: victorias del local en los últimos 5 enfrentamientos previos contra el rival.
- `h2hDraws`: empates en los últimos 5 enfrentamientos previos.
- `h2hAwayWins`: victorias del visitante en esos enfrentamientos.
- `h2hMatches`: número real de enfrentamientos disponibles, entre 0 y 5.

Se considerarán ambos sentidos del enfrentamiento: si el partido anterior se disputó con los equipos invertidos, se transformará el resultado para expresarlo desde la perspectiva del local actual.

## Regla contra fuga de información

El procesamiento debe mantener dos historiales separados:

1. Historial de cada equipo: se consulta antes de registrar el partido actual.
2. Historial del par de equipos: se consulta antes de registrar el partido actual.

Al igual que en el bloque #8, todos los partidos de una misma jornada consultarán el estado existente al inicio de la jornada. Los resultados de esa jornada se añadirán a los historiales únicamente después de construir todos sus objetos [`Partido`](../src/football_dataset/FootballClasses.py:27).

No se utilizarán:

- el marcador del partido actual para calcular sus propias variables;
- partidos posteriores de la temporada;
- resultados futuros para completar ventanas incompletas;
- el estado final de la clasificación.

## Diseño de implementación

### Modelo

Ampliar [`Partido`](../src/football_dataset/FootballClasses.py:27) con:

- `rachaLocal: int`
- `rachaVisitante: int`
- `formaLocal: str`
- `formaVisitante: str`
- `h2hLocalWins: int`
- `h2hDraws: int`
- `h2hAwayWins: int`
- `h2hMatches: int`

Los campos tendrán valores por defecto compatibles con partidos creados por consumidores antiguos: `0`, `0`, `""` y `0`.

### Procesamiento de temporada

En [`DatosTemporada.py`](../src/football_dataset/DatosTemporada.py:18):

- Añadir un historial por equipo con entradas `(resultado, puntos)`.
- Añadir un historial por pareja de equipos con entradas `(fecha/orden, resultado desde local actual)`.
- Crear helpers puros o métodos privados para obtener las últimas 5 entradas.
- Ampliar [`addMatch()`](../src/football_dataset/DatosTemporada.py:80) para calcular las variables antes de mutar historiales.
- Durante [`loadMatches()`](../src/football_dataset/DatosTemporada.py:48), construir todos los partidos de la jornada leyendo el mismo snapshot de historiales y actualizar los historiales al terminar la jornada.

La clave de H2H será un par ordenado e independiente del sentido del partido, por ejemplo `(min(id1, id2), max(id1, id2))`. El resultado almacenado debe conservar quién ganó para poder invertirlo según el local actual.

### Exportación

Añadir los nuevos campos a [`HEADERS`](../src/football_dataset/dataset_io.py:9), manteniendo las columnas históricas previas antes de los datos del resultado actual.

## Tests requeridos

En [`tests/test_refactor_closure.py`](../tests/test_refactor_closure.py:1) o en un test dedicado:

1. La racha del primer partido es vacía/cero.
2. La racha de un partido usa sólo partidos anteriores.
3. Dos partidos de la misma jornada reciben el mismo snapshot de forma e H2H antes de aplicar resultados de esa jornada.
4. La ventana nunca supera 5 partidos.
5. Un enfrentamiento anterior con local/visitante invertidos se transforma correctamente.
6. Un partido actual no altera sus propias variables H2H.
7. La exportación CSV incluye todas las columnas nuevas.

## Estado

Implementado y validado. La suite offline pasa con 14 tests y los tests de integración permanecen excluidos por defecto.

## Criterios de aceptación

- Las variables de racha e H2H son reproducibles y no dependen del orden accidental de iteración dentro de una jornada.
- Ningún valor usa información posterior al partido analizado.
- Los historiales incompletos se representan con `h2hMatches` y cadenas de forma de longitud real, sin inventar resultados.
- La suite offline (`python -m pytest -q`) permanece verde.
- Se actualizan [`README.md`](../README.md:1) y [`TODOS.md`](../TODOS.md:76) al finalizar.
