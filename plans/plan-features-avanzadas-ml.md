# Plan: ingeniería de características avanzada para 1X2 (bloque #22)

## Diagnóstico

Las métricas actuales (balanced accuracy ~0.40, log loss ~1.02-1.05) están cerca
de un predictor aleatorio. El walk-forward ya es correcto, así que el problema
no es la validación sino la **señal disponible para el modelo**.

El artefacto [`dataset_ml.csv`](../data/dataset_ml.csv) reduce los goles a
`diferenciaGolesNeta` y las rachas a un balance global. Se pierden:

- la condición casa/fuera específica de cada equipo;
- la dinámica ofensiva y defensiva por separado;
- el calendario/fatiga;
- la relación entre valor de mercado y rendimiento real.

El dataset fuente enriquecido sí contiene la materia prima (`matchDate`, goles
acumulados por equipo, valores de mercado y posiciones), pero
[`ml_features.py`](../src/football_dataset/ml_features.py:1) la descarta o la
agrega antes de tiempo.

## Principios

- Todas las nuevas variables se calculan **solo con información previa** al
  partido, con snapshot por jornada (igual que los bloques #8, #9 y #10).
- La condición casa/fuera se respeta: una racha "como local" no se mezcla con
  partidos como visitante.
- Se añaden al esquema fuente y se trasladan al ML, **sin** alterar la semántica
  de las columnas existentes.

## Variables nuevas propuestas

### 1. Dinámica de goles (medias móviles)

Derivar por equipo, usando los últimos 5 y 10 partidos previos:

- `golesFavor5Local`, `golesContra5Local`, `golesFavor10Local`, `golesContra10Local`;
- análogas para el visitante.

Capturan ofensiva y defensa por separado, en lugar de la resta neta. Se
mantienen como features adicionales, no como sustituto de
`diferenciaGolesNeta`.

### 2. Condición casa/fuera

- `rachaLocalCasa`: balance de los últimos N partidos del local **jugando como
  local** antes del partido.
- `rachaVisitanteFuera`: balance de los últimos N partidos del visitante
  **jugando como visitante**.
- `partidosCasaLocal` / `partidosFueraVisitante`: número real de partidos
  disponibles en esa condición (contigüedad sin invención).

### 3. Calendario y fatiga

Usando `matchDate`:

- `diasDescansoLocal`: días desde el último partido oficial anterior del local.
- `diasDescansoVisitante`: idem visitante.
- `partidos7DiasLocal` / `partidos7DiasVisitante`: partidos en los últimos 7
  días naturales.
- `diferenciaDescanso = diasDescansoLocal - diasDescansoVisitante`.

### 4. Rendimiento frente a mercado

- `puntosEsperadosLocal` / `puntosEsperadosVisitante`: proxy del valor de
  mercado normalizado por división y jornada.
- `sobreRendimientoLocal` / `sobreRendimientoVisitante`: puntos reales menos
  esperados. Captura equipos que rinden por encima o por debajo de su plantilla.

El proxy se documentará como aproximación (el valor de mercado no es una
esperanza formal de puntos).

## Cambios en el núcleo

1. [`FootballClasses.py`](../src/football_dataset/FootballClasses.py:27):
   - nuevos campos por defecto compatibles.
2. [`DatosTemporada.py`](../src/football_dataset/DatosTemporada.py:18):
   - historial casa/fuera por equipo;
   - medias por ventana y días de descanso desde snapshots congelados.
3. [`dataset_io.py`](../src/football_dataset/dataset_io.py:19):
   - añadir columnas y subir `SCHEMA_VERSION` a `4`.
4. [`enrichment.py`](../src/football_dataset/enrichment.py:47):
   - migración v3 → v4 offline con valores neutros documentados.
5. [`ml_features.py`](../src/football_dataset/ml_features.py:23):
   - incluir las nuevas columnas en `ML_COLUMNS` y su cálculo determinista.

## Criterio de éxito

- Las nuevas features no filtran información del partido actual ni de jornadas
  posteriores (tests de no fuga).
- El log loss/balanced accuracy sobre walk-forward **mejora respecto al modelo
  actual con las mismas particiones y seeds**.
- La suite y Ruff verdes; el esquema migra v3→v4 sin red.

## Fuera de alcance (documentado)

xG, lesiones, posesión y alineaciones: no están disponibles en el dataset
actual. Se reservan para [`plan-datos-avanzados.md`](plan-datos-avanzados.md:1).