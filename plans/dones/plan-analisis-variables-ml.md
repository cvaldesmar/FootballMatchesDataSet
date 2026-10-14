# Plan: análisis y simplificación de variables para Machine Learning (bloque #19)

## Objetivo

Auditar de forma específica el dataset actual ([`HEADERS`](../src/football_dataset/dataset_io.py:13)) para decidir, variable a variable y por bloques:

1. Qué columnas son útiles como características para el pronóstico `1X2`.
2. Qué variables sintéticas conviene crear a partir de las existentes.
3. Qué columnas aportan poco, son redundantes o confunden al modelo.
4. Qué transformaciones de limpieza, codificación o reducción conviene aplicar antes del modelado.

El resultado es un dataset más enfocado, interpretable y con mejor relación señal/ruido, sin cambiar la fuente de verdad original (los CSV se preservan y el dataset simplificado se genera aparte).

## Inventario actual de columnas

### 1. Identificadores y contexto temporal

| Columna | Tipo | Rol para ML | Decisión propuesta |
|---|---|---|---|
| `idPartido` | entero | identificador | No usar como feature. Conservar para trazabilidad y división de datos. |
| `division` | entero (1/2) | contexto | Conservar como feature categórica o para filtrar por división. |
| `temporada` | cadena | contexto temporal | No usar directamente. Usar para ordenar, dividir cronológicamente y construir features temporales. |
| `jornada` | entero | contexto temporal | Conservar (fase de temporada). |
| `matchDate` | fecha | contexto temporal | No usar directamente. Derivar `diaSemana`, `mes`, `diasDesdeInicioTemporada`. |

### 2. Equipos

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `localName`, `visitanteName` | claves naturales | No usar como features crudas. Conservar para trazabilidad y mapeo. |
| `localId`, `visitanteId` | identidad semántica | Usar como base para agregaciones históricas, no como variables crudas directas (evitar cardinalidad alta sin incrustaciones). |

### 3. Estado de forma y clasificación (pre-partido)

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `puntosLocal`, `puntosVisitante` | rendimiento acumulado | Conservar. |
| `posicionLocal`, `posicionVisitante` | rango de tabla | Conservar. |
| `diferenciaPuntos` | distancia competitiva | Conservar (referencia la del local, pero documentar). |
| `golesafavorlocal`, `golesencontralocal`, `golesafavorvisitante`, `golesencontravisitante` | ataque/defensa acumulado | Conservar. Posible transformar en `diferenciaGolesLocal/Visitante`. |
| `rachaLocal`, `rachaVisitante` | dinámica corta | Conservar. |
| `formaLocal`, `formaVisitante` | trend reciente encodado | Conservar o convertir a features numericas (`victorias`, `empates`, `derrotas`, `ratioPuntos`). |

### 4. Historial H2H

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `h2hLocalWins`, `h2hDraws`, `h2hAwayWins`, `h2hMatches` | histórico directo | Conservar agrupadas. Valorar consolidar en ratios: `h2hRatioLocal`, `h2hRatioEmpate`, `h2hRatioVisitante`. |

### 5. Contexto competitivo

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `campeonId` | campeón decidido | Conservar como indicador binario `campeonYaDecidido` y/o distancia en puntos al campeón. |
| `descensoConfirmadoLocal`, `descensoConfirmadoVisitante` | descenso matemático | Conservar como binarias o combinarlas. |
| `presionLocal`, `presionVisitante` | presión competitiva | Conservar. |

### 6. Rivalidad y desplazamiento

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `rivalidad` | binaria | Conservar. |
| `distanciaKm` | desplazamiento del visitante | Conservar. Para ML, decidir si imputar los `-1` o convertir la ausencia en categoría. |

### 7. Mercado y arbitraje

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `localMarketValue`, `visitanteMarketValue` | valor de plantilla | Conservar como `diferenciaValorMercado` y `ratioValorMercado`; evitar usar los dos valores por separado si introducen colinealidad. |
| `arbitroName` | identidad | No usar como feature cruda. Puede agregarse por historial del árbitro (tarjetas/resultados) solo si se dispone de cobertura. |
| `arbitroId` | identidad | No usar directamente. Conservar para trazabilidad. |

### 8. Resultado (etiqueta y auxiliares)

| Columna | Rol | Decisión propuesta |
|---|---|---|
| `golesLocal`, `golesVisitante` | resultado | Conservar como salida auxiliar; derivar `resultado1X2`. |
| `golDiff` | diferencia | Conservar para métricas de regresión o modelos de marcador. |
| `resultado1X2` (pendiente de añadir) | **objetivo** | Añadir en esquema v3 (ver [`plan-calidad-dataset-ml.md`](plan-calidad-dataset-ml.md:1)). |

## Variables sintéticas propuestas

Deben calcularse solo con información previa al partido.

### Relativas a forma y momento

- `ratioPuntosLocal` / `ratioPuntosVisitante`: puntos obtenidos / puntos disputados.
- `mediaPuntosUltimos5Local` / `mediaPuntosUltimos5Visitante`.
- `mediaGolesFavorUltimos5Local` / `mediaGolesFavorUltimos5Visitante`.
- `mediaGolesContraUltimos5Local` / `mediaGolesContraUltimos5Visitante`.
- `tendenciaLocal` / `tendenciaVisitante`: diferencia entre media reciente (5) y media larga (10-15).

### Relativas a capacidad ofensiva y defensiva

- `diferenciaGolesLocal` / `diferenciaGolesVisitante`: `golesFavor - golesContra`.
- `efectividadOfensivaLocal` / `efectividadOfensivaVisitante`: goles favor / partidos.
- `rigidezDefensivaLocal` / `rigidezDefensivaVisitante`: goles contra / partidos.
- `balanceLocal` / `balanceVisitante`: `efectividadOfensiva - rigidezDefensiva`.

### Relativas al contraste entre equipos

- `diferenciaValorMercado` y `ratioValorMercado`.
- `diferenciaPosicion`: `posicionVisitante - posicionLocal`.
- `diferenciaForma`: `rachaLocal - rachaVisitante` y/o diferencia de `ratioPuntos`.
- `ventajaLocal`: factor combinado que mezcle localía, distancia y forma (documentar cómo se construye).

### Relativas a legado histórico

- `aniosDesdeUltimoTituloLocal` / `aniosDesdeUltimoTituloVisitante`.
- `titulosHistoricosLocal` / `titulosHistoricosVisitante`.
- `diferenciaTitulosHistoricos`.

(Detalle en [`plan-calidad-dataset-ml.md`](plan-calidad-dataset-ml.md:71)).

### Relativas a calendario y desgaste

- `diasDescansoLocal` / `diasDescansoVisitante`: días desde su último partido oficial.
- `partidosUltimos7DiasLocal` / `partidosUltimos7DiasVisitante`.
- `diferenciaDescanso`: `diasDescansoLocal - diasDescansoVisitante`.
- `diasDesdeInicioTemporada`: etapa de la temporada.

(Estas requieren añadir la fecha de partido ya disponible en `matchDate`.)

## Variables candidatas a eliminar o no usar

- `idPartido`, `localName`, `visitanteName`, `localId`, `visitanteId`, `arbitroName`, `arbitroId`, `temporada` y `matchDate` **como features crudas**: solo de contexto y trazabilidad.
- Redundancias detectables:
  - `puntosLocal`/`puntosVisitante` ya correlacionan con `posicionLocal`/`posicionVisitante`; evaluar si mantener ambos o derivar uno.
  - `golesafavorlocal` + `golesencontralocal` se pueden consolidar en `diferenciaGolesLocal`; `golesafavorvisitante` + `golesencontravisitante` en `diferenciaGolesVisitante`.
  - `h2hLocalWins`, `h2hDraws`, `h2hAwayWins` ya se derivan de `h2hMatches`; valorar conservar ratios en lugar de conteos crudos para reducir dimensionalidad.
- Variables de mercado por separado (`localMarketValue`, `visitanteMarketValue`) si se introduce su diferencia/ratio; evaluar colinealidad.
- Metadata de árbitros hasta no disponer de historial agregado fiable.

## Simplificación y codificación para el pipeline

1. **Codificación temporal**:
   - Convertir `matchDate` a `año`, `mes`, `díaSemana` y `diasDesdeInicioTemporada`.
2. **Normalización de ausencias**:
   - `-1` (o cadena vacía) como marcador explícito de ausencia; generar columnas binarias `es_ausente_<campo>` cuando sea relevante.
3. **Escalado**:
   - `distanciaKm`, valores de mercado y goles acumulados mediante min-max o z-score (a decidir en el pipeline de ML, no en el CSV).
4. **Codificación de categorías**:
   - `division`, `rivalidad`, `descensoConfirmado*`, `presion*` como categóricas ordinals o one-hot.
   - `resultado1X2` como etiqueta multiclase (`1`, `X`, `2`).
5. **Orden temporal**:
   - Asegurar orden cronológico y añadir índice `fecha_partido_orden` si es necesario para división temporal sin fugas.

## Entregables

- Fichero de audiencia de variables (p. ej. `docs/analisis_variables.md`) con la tabla de decisión por columna.
- Función `build_ml_features()` y módulo de transformación (p. ej. `src/football_dataset/ml_features.py`) que, partiendo del CSV enriquecido, genere un dataset simplificado con las columnas seleccionadas y las sintéticas.
- Comando CLI dedicado que admita ejecutar **solo** la generación de features de ML a partir de un CSV ya existente.
- Gancho en la ejecución principal ([`Main.py`](../src/football_dataset/Main.py:1)) para que, opcionalmente, al final de la generación del dataset inicial se invoque a `build_ml_features()` y se produzca el dataset ML en paralelo.
- Tests de que las features sintéticas no cambian al reordenar partidos y de que las columnas reducido/dimensiones coinciden.
- Máscara de columnas a excluir del ML (identificadores y texto crudo).

## Dos formas de generar el dataset ML

El dataset histórico/enriquecido es la **fuente de verdad inmutable**; el dataset ML es un artefacto derivado. Se contemplan dos modos:

1. **Modo independiente o bajo demanda**:
   - `python -m src.football_dataset.ml_features --input data/dataset_historico_1970_2025_enriquecido.csv --output data/dataset_ml.csv`
   - Útil cuando el dataset fuente ya está generado y solo se desea recalcular o afinar las features.

2. **Modo integrado en la generación principal**:
   - Nuevo flag `--build-ml` en [`Main.py`](../src/football_dataset/Main.py:1).
   - Al terminar la generación del dataset base/enriquecido, el programa invoca automáticamente a [`build_ml_features()`](../src/football_dataset/ml_features.py:1) y escribe el dataset ML junto al resto de artefactos.
   - Admite `--ml-output` para indicar la ruta de salida; si no se especifica, usa una derivada por convención (p. ej. `data/dataset_ml.csv`).

En ambos modos:

- La salida ML nunca sobrescribe el CSV fuente.
- Se valida que el CSV fuente tenga el esquema esperado antes de transformar.
- La transformación es determinista, sin red y con tests de no fuga temporal.

## Arquitectura de transformación propuesta

```text
CSV histórico/enriquecido (fuente de verdad, esquema v3)
                    |
                    v
        build_ml_features()
                    |
        + selección de columnas
        + codificación temporal
        + normalización de ausencias
        + features sintéticas (solo histórico previo)
        + resultado1X2 como etiqueta
                    |
                    v
        dataset_ml.csv (artefacto derivado)
```

El pipeline queda así separado del scraping y de la persistencia base, permitiendo iterar sobre las features sin volver a descargar ni alterar el dataset original.

## Criterios de aceptación

- [x] Cada columna actual está clasificada: feature / sintética / contexto / etiqueta.
- [x] Las variables sintéticas implementadas tienen fórmula explícita y usan solo información previa.
- [x] Las columnas redundantes se han consolidado en un conjunto relativo de 20 columnas.
- [x] El dataset simplificado se genera aparte sin alterar el CSV histórico.
- [x] La transformación es determinista, offline y está cubierta por tests.
- [x] Existe CLI dedicada y flag integrado `--build-ml`.

## Estado

**Implementado.** El artefacto [`data/dataset_ml.csv`](../../data/dataset_ml.csv) contiene 43.884 filas y 20 columnas: 19 variables de contexto/features y la etiqueta `resultado1X2`.