# Plan: calidad del dataset para aprendizaje automático (bloque #18)

## Objetivo

Preparar [`dataset_historico_1970_2025_enriquecido.csv`](../data/dataset_historico_1970_2025_enriquecido.csv) para entrenar un modelo de pronóstico de resultado **1X2** de partidos de fútbol, garantizando una estructura de columnas clara, coherente, sin fugas de información y lista para su consumo en un pipeline de ML.

La variable objetivo es el resultado del partido visto desde la perspectiva del equipo local:

- `1` — victoria local.
- `X` — empate.
- `2` — victoria visitante.

## Contexto actual (a verificar)

El dataset ya incluye la mayoría de las variables de enriquecimiento:

- Variables históricas previas congeladas por jornada.
- Rachas y forma (`rachaLocal`, `formaLocal`, etc.).
- H2H sin fuga de información.
- Contexto competitivo (`campeonId`, descensos confirmados, presión).
- Rivalidad binaria.
- Distancia de viaje del visitante.
- Goles y diferencia de goles.

Falta la variable objetivo explícita `resultado1X2`. Actualmente el resultado solo es derivable indirectamente desde `golesLocal` y `golesVisitante`, lo que obliga a cada futuro modelo a recalcularlo y facilita errores de etiquetado.

## Componentes del trabajo

### 0. Inventario de mejoras de calidad para ML

Añadir progresivamente, siempre como variables exclusivamente pre-partido y sin fuga de información:

- **Legado histórico**: años desde el último título y total de títulos históricos.
- **Dinámica de largo plazo**: media móvil de puntos, media móvil de goles a favor/en contra, tendencia de forma en ventanas amplias (por ejemplo, 10 o 15 partidos).
- **Efectividad ofensiva/defensiva relativa**: goles esperados simplificados a partir de goles a favor/en contra, cocientes ofensivo/defensivo previos.
- **Rentabilidad como local/visitante**: porcentaje de puntos conseguidos en casa y fuera antes del partido.
- **Colchón competitivo respecto a descenso y puestos europeos**: distancia en puntos al descenso o a competiciones (si se incorpora Europa).
- **Desgaste por calendario**: días de descanso desde el último partido de cada equipo, número de partidos en los últimos N días.
- **Plantilla y mercado**: ratio y diferencia de valor de mercado entre local y visitante.
- **Estabilidad del once o del cuerpo técnico**: solo si se dispone de fuente oficial con cobertura suficiente (dejar documentado como opcional).

Estas variables deben acompañarse de un diccionario de datos y de la correspondiente verificación de no fuga temporal.

### 1. Variable objetivo explícita

Añadir la columna `resultado1X2` a [`HEADERS`](../src/football_dataset/dataset_io.py:13):

- `1` si `golesLocal > golesVisitante`.
- `X` si `golesLocal == golesVisitante`.
- `2` si `golesLocal < golesVisitante`.

Se mantendrán `golesLocal`, `golesVisitante` y `golDiff` para poder modelar también marcadores exactos o servir de métricas auxiliares, pero `resultado1X2` será la etiqueta canónica.

### 2. Estructura de columnas por bloques

Organizar la documentación del CSV en bloques semánticos:

1. **Identificadores y contexto**: `idPartido`, `division`, `temporada`, `jornada`, `matchDate`.
2. **Equipos**: `localName`, `localId`, `visitanteName`, `visitanteId`.
3. **Variables de partido (pre-partido)**:
   - Estado de forma y clasificación: `puntosLocal`, `posicionLocal`, `diferenciaPuntos`, `rachaLocal`, `formaLocal`, etc.
   - Historial H2H: `h2hLocalWins`, `h2hDraws`, `h2hAwayWins`, `h2hMatches`.
   - Contexto competitivo: `campeonId`, `descensoConfirmado*`, `presion*`.
   - Rivalidad y desplazamiento: `rivalidad`, `distanciaKm`.
   - Mercado y árbitros: `localMarketValue`, `visitanteMarketValue`, `arbitroName`, `arbitroId`.
   - **Legado histórico del club** (nuevas propuestas): `aniosDesdeUltimoTituloLocal`, `aniosDesdeUltimoTituloVisitante`, `titulosHistoricosLocal`, `titulosHistoricosVisitante`.
4. **Resultado**: `golesLocal`, `golesVisitante`, `golDiff`, `resultado1X2`.

Esta taxonomía permite separar claramente qué variables son características y cuál es la etiqueta.

### 2.1. Variables de legado histórico del club

No existe actualmente ninguna variable que indique cuánto tiempo hace que un equipo fue campeón por última vez. Se propone añadir, usando únicamente información previa al partido:

- `aniosDesdeUltimoTituloLocal` / `aniosDesdeUltimoTituloVisitante`:
  - `0` si el equipo es el campeón vigente.
  - `1` si lo fue la temporada anterior.
  - `n` en general, número de temporadas completas transcurridas desde su último campeonato.
  - `-1` si nunca consta campeón o no hay información histórica suficiente.
- `titulosHistoricosLocal` / `titulosHistoricosVisitante`:
  - número total de campeonatos ganados antes del partido actual.
  - `-1` cuando no se disponga de la serie completa.

Estas variables capturan "inercia ganadora" o prestigio histórico, que es un factor cualitativamente distinto del estado de forma reciente y del contexto competitivo de la temporada en curso. Deben derivarse solo de palmarés previo para no filtrar el resultado actual.

### 3. Calidad y codificación de datos

- **Valores ausentes**: unificar `-1`, `N/D` y cadenas vacías como ausencia explícita con una semántica documentada.
- **Tipos**: garantizar enteros para IDs, `float` para distancias y valores de mercado, cadenas normalizadas para nombres.
- **`distanciaKm == -1`**: documentar que significa "sin coordenadas históricas" y considerar en ML el tratamiento de frecuencia e imputación.
- **`localMarketValue == -1`**: ausencia de valor de mercado; no confundir con valor cero.
- **Nombres**: mantener `localName`/`visitanteName` como clave natural, y los IDs como clave estable de modelado.

### 4. Prevención y auditoría de fuga de información

Añadir una validación `anti_leakage` que garantice:

- Ninguna variable pre-partido usa el resultado del partido actual.
- Las rachas, forma y H2H solo observan jornadas anteriores.
- `campeonId`, descensos y presión solo usan clasificación previa.
- `distanciaKm`, mercado y árbitro se calculan sin información del resultado.

Se verificará configurando explícitamente un snapshot por jornada y comprobando en tests que, al reordenar un resultado, las features previas no cambian.

### 5. Consistencia temporal y orden

- Verificar que los partidos están ordenados por temporada y jornada.
- Asegurar que no hay duplicados de (`temporada`, `division`, `jornada`, local, visitante).
- Añadir un campo opcional `fecha_partido_orden` o un índice cronológico interno si el modelo lo necesita para división temporal.

### 6. Esquema de salida

Incrementar [`SCHEMA_VERSION`](../src/football_dataset/dataset_io.py:10) a `3` al añadir `resultado1X2`.

Extender el migrador evolutivo [`migrate_csv_schema()`](../src/football_dataset/enrichment.py:47) para migrar datasets v2 a v3 calculando la etiqueta a partir de los goles, sin red y sin regenerar nada.

### 7. Documentación del proyecto como generador para ML

Actualizar [`README.md`](../README.md:1) y [`TODOS.md`](../TODOS.md:1) para declarar explícitamente que:

- El proyecto genera un dataset para pronóstico de resultado 1X2.
- La variable objetivo es `resultado1X2`.
- Las características previas están congeladas para evitar fuga temporal.

## Cambios propuestos

1. [`src/football_dataset/dataset_io.py`](../src/football_dataset/dataset_io.py:1):
   - Añadir `resultado1X2`.
   - `SCHEMA_VERSION = 3`.

2. [`src/football_dataset/FootballClasses.py`](../src/football_dataset/FootballClasses.py:1):
   - Añadir campo `resultado1X2` derivado en `__post_init__`.

3. [`src/football_dataset/DatosTemporada.py`](../src/football_dataset/DatosTemporada.py:1):
   - Asignar la etiqueta al construir cada partido.

4. [`src/football_dataset/enrichment.py`](../src/football_dataset/enrichment.py:1):
   - Migrar v2→v3.
   - Complementar validación anti-fuga.

5. [`src/football_dataset/validation.py`](../src/football_dataset/validation.py:1):
   - Añadir chequeos de consistencia de la etiqueta y de valores ausentes por columna.

6. [`tests/`](../tests/):
   - Tests de derivación de `resultado1X2`.
   - Test de migración v2→v3.
   - Test anti-fuga.

## Criterios de aceptación

- El CSV exportado contiene la columna `resultado1X2` con valores `1`, `X` o `2`.
- `resultado1X2` es coherente con `golesLocal` y `golesVisitante` en el 100% de las filas.
- El esquema queda versionado en `3`.
- La migración v2→v3 se ejecuta sin red ni re-scraping.
- La suite (`pytest` y `ruff`) permanece verde.
- La documentación describe la variable objetivo y la taxonomía de columnas para ML.