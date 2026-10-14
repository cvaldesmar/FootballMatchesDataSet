# Plan: estrategia de modelado y objetivo para 1X2 (bloque #23)

## Diagnóstico

El empate es la clase minoritaria y más ruidosa del problema. Un clasificador
multiclase directo tiende a ignorarla, arrastrando la `balanced_accuracy` y el
`log_loss`. Gemini propone dos vías válidas:

1. enfoque de dos etapas (¿empate? → ¿gana local o visitante?);
2. modelar goles (Poisson bivariante) y derivar 1X2.

Ambas se evaluarán sobre el mismo walk-forward y se compararán contra el
clasificador multiclase actual mediante el score combinado.

## Objetivo

Mejorar la capacidad de predecir correctamente el empate y la calidad de las
probabilidades, no solo el acierto global.

## Propuesta 1: clasificador de dos etapas (prioritario)

- Modelo 1 (binario): predice `no_empate`/`empate` con probabilidad `p_draw`.
- Modelo 2 (binario, solo ejemplos sin empate): predice `local`/`visitante`.
- Combinación final de probabilidades 1X2:

```text
P(1) = (1 - p_draw) * p_local
P(X) = p_draw
P(2) = (1 - p_draw) * p_visitante
```

Ventajas: cada etapa es un problema binario más sencillo; el empate obtiene su
propio modelo dedicado. Se entrena/valida por separado respetando el orden
temporal.

## Propuesta 2: goles esperados (Poisson)

- Regresión de `golesLocal` y `golesVisitante` con `PoissonRegressor` o
  `HistGradientBoostingRegressor` sobre el log de la media.
- Derivar la probabilidad 1X2 mediante la matriz de Poisson bivariante
  (independencia asumida) o una suma truncada.

Se evalúa como alternativa; requiere más trabajo y su ganancia no está
garantizada sin variables de calidad ofensiva/defensiva (ver bloque #22).

## Ajustes independientes y de bajo coste

- **Early stopping** en XGBoost y LightGBM sobre un tramo final temporal del
  entrenamiento (sin tocar la ronda a predecir).
- **Umbral del empate**: en lugar de `argmax`, explorar un offset sobre
  `P(X)` para compensar la baja frecuencia de empates y maximizar
  `balanced_accuracy` en validación.
- **Priorizar modelos rápidos**: más trials en LightGBM/XGBoost; fewer en
  Random Forest y GradientBoosting clásico.
- **Ventana temporal**: comparar `--last-seasons 4`, `5`, `8` y `12`.

## Criterio de decisión

Se adopta la estrategia que obtenga el mejor `combined` en walk-forward, con el
mismo holdout final intocable. La comparación incluirá el clasificador
multiclase actual como referencia.

## Cambios previstos

- [`src/football_ml/staged.py`](../src/football_ml/staged.py:1): pipeline de dos etapas.
- [`src/football_ml/poisson.py`](../src/football_ml/poisson.py:1): goles esperados y derivación 1X2.
- [`src/football_ml/models.py`](../src/football_ml/models.py:1): early stopping configurable.
- [`src/football_ml/tuning.py`](../src/football_ml/tuning.py:1): trials por modelo y umbral del empate.
- Tests de no fuga y de coherencia de probabilidades (suman 1).

## Fuera de alcance

Modelado con cuotas de casas de apuestas como feature o target; requiere una
fuente adicional autorizada.