# Plan: optimización temporal de modelos 1X2

## Estado

Implementado. El sistema explora modelos e hiperparámetros mediante validación
walk-forward por jornada y selecciona un campeón con Optuna.

## Objetivo

Elegir el modelo que mejor simula el uso real: entrenar con todo lo conocido
antes de una jornada y predecir únicamente la jornada siguiente. No se usa una
división aleatoria ni se permite que una jornada futura contamine el entrenamiento.

## Componentes implementados

- [`score.py`](../src/football_ml/score.py:1): score combinado
  `balanced_accuracy - log_loss / ln(3)`. Un valor mayor es mejor.
- [`walk_forward.py`](../src/football_ml/walk_forward.py:1): agrupa por
  `(temporada, jornada)`, entrena con rondas anteriores y valida en la siguiente.
  Soporta `min_train_rounds`, `max_train_rounds` y `max_validation_rounds`.
- [`models.py`](../src/football_ml/models.py:1): fábricas parametrizables para
  Logistic Regression, Random Forest, HistGradientBoosting, XGBoost y LightGBM.
- [`tuning.py`](../src/football_ml/tuning.py:1): búsqueda Optuna con TPE y
  `MedianPruner`; guarda parámetros, métricas, rondas y catálogo de resultados.
- [`__main__.py`](../src/football_ml/__main__.py:1): subcomando `tune`.
- [`next_round.py`](../src/football_ml/next_round.py:1): reutiliza el campeón
  persistido y solo reentrena si se especifica `--retrain`.
- [`requirements-ml.txt`](../requirements-ml.txt:1): dependencias opcionales
  `optuna`, `xgboost` y `lightgbm` aisladas del scraper.

## Flujo recomendado

### 1. Actualizar datos

Actualizar el histórico enriquecido con todos los partidos finalizados hasta la
fecha de corte. Preparar un CSV de fixtures futuras sin goles ni etiqueta.

### 2. Optimizar periódicamente

La optimización es costosa y no debe ejecutarse cada jornada automáticamente.
Debe ejecutarse al inicio de temporada, tras incorporar suficiente información
nueva o cuando el rendimiento walk-forward se degrade.

```text
python -m src.football_ml tune \
  --input data/dataset_ml.csv \
  --last-seasons 12 \
  --models logistic random-forest gradient-boosting xgboost lightgbm \
  --trials-per-model 50 \
  --min-train-rounds 10 \
  --model data/campeon.joblib
```

El comando:

1. descarta temporadas antiguas según `--last-seasons` o `--min-season`;
2. ejecuta walk-forward por jornadas;
3. explora los espacios de hiperparámetros con Optuna;
4. compara los cinco modelos mediante el score combinado;
5. reajusta el ganador sobre toda la ventana seleccionada;
6. persiste el campeón y sus metadatos.

### 3. Predecir cada jornada

```text
python -m src.football_ml next-round \
  --history data/dataset_historico_actualizado_enriquecido.csv \
  --fixtures data/fixtures_next_round.csv \
  --model data/campeon.joblib \
  --as-of 2026-10-14 \
  --output data/predicciones_jornada.csv
```

Por defecto carga el modelo existente. `--retrain` permite sustituirlo por un
entrenamiento directo, pero no lanza Optuna; para cambiar modelo o parámetros se
usa explícitamente `tune`.

## Validación y anti-fuga

Para cada ronda `R_i`:

```text
train = rondas anteriores a R_i
valid = todos los partidos de R_i
fit(train) -> predict(valid)
```

El holdout final debe reservarse para una evaluación posterior a la selección.
Las features de fixtures futuras se construyen con histórico limitado por
`matchDate <= as_of`; ningún partido posterior puede afectar a la predicción.

## Criterios de aceptación

- El campeón se selecciona por walk-forward, no por un split aleatorio.
- Los parámetros y métricas quedan persistidos.
- Las probabilidades de 1/X/2 son válidas y suman 1.
- `next-round` reutiliza el campeón sin optimizar en cada ejecución.
- Hay tests del score, orden temporal, smoke test de Optuna y anti-fuga.
- Ruff y pytest permanecen verdes.

## Riesgos

- La búsqueda completa puede ser costosa: reducir `--trials-per-model`, limitar
  `--max-validation-rounds` durante una exploración inicial y usar pruneo.
- El score combinado no sustituye una evaluación final en un holdout temporal.
- XGBoost y LightGBM deben compararse contra los baselines y no aceptarse solo
  por mayor accuracy: también importa la calibración de probabilidades.
