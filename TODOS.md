# Trabajo pendiente

Consulta el histórico de tareas completadas en [`TODO-DONES.md`](TODO-DONES.md:1).

Este archivo contiene únicamente los bloques pendientes y sus posibles ampliaciones.

## Bloque 4 — Persistencia, documentación y operación

### 12. Comando de diagnóstico

- [ ] Comprobar conectividad con las fuentes.
- [ ] Comprobar existencia y versión de cachés.
- [ ] Comprobar temporadas disponibles.
- [ ] Ejecutar validaciones rápidas de entrada y salida.

**Plan de implantación:** [`plan-diagnostico.md`](plans/plan-diagnostico.md:1).

### 13. Documentación de datos

- [ ] Documentar todas las fuentes utilizadas.
- [ ] Documentar limitaciones, cobertura histórica y frecuencia de actualización.
- [ ] Documentar el significado, tipo y unidad de cada columna.
- [ ] Documentar las posibles limitaciones legales y técnicas del scraping.

**Plan de implantación:** [`plan-documentacion-datos.md`](plans/plan-documentacion-datos.md:1).

## Bloque 5 — Enriquecimiento opcional

### 16. Estación y variables climáticas

- [ ] Añadir estación del año.
- [ ] Evaluar datos climáticos históricos por sede y fecha.
- [ ] Documentar cobertura y valores ausentes.

**Plan de implantación:** [`plan-estacion-clima.md`](plans/plan-estacion-clima.md:1).

### 17. Datos avanzados de partido

- [ ] Evaluar fuentes históricas de lesiones y sanciones.
- [ ] Evaluar posesión, disparos, alineaciones y cambios tácticos.
- [ ] Incorporar únicamente variables con cobertura y calidad suficientes.

**Plan de implantación:** [`plan-datos-avanzados.md`](plans/plan-datos-avanzados.md:1).

## Bloque 6 — Preparación para aprendizaje automático

### 19. Análisis y simplificación de variables para ML

- [x] Auditar cada columna actual y clasificar su rol (feature / contexto / etiqueta).
- [x] Proponer variables sintéticas previas al partido con fórmula explícita.
- [x] Identificar columnas redundantes o de baja utilidad para consolidar o excluir.
- [x] Definir codificación, escalado y orden temporal para el pipeline de ML.
- [x] Generar un dataset simplificado aparte sin alterar el CSV histórico.
- [x] Integrar la generación vía CLI dedicada (`ml_features`) y flag opcional (`--build-ml`) en la ejecución principal.

**Plan archivado:** [`plan-analisis-variables-ml.md`](plans/dones/plan-analisis-variables-ml.md:1). Implementado.

## Bloque 7 — Pipeline de aprendizaje automático

### 20. Entrenamiento, evaluación y predicción temporal

- [x] Crear paquete separado [`src/football_ml/`](src/football_ml) para consumir `dataset_ml.csv`.
- [x] Aislar dependencias de ML en [`requirements-ml.txt`](requirements-ml.txt:1).
- [x] Descartar histórico antiguo antes del preprocesado mediante `--min-season` o `--last-seasons`.
- [x] Separar train/validación/test por temporadas sin barajar la serie temporal.
- [x] Entrenar modelos Logistic Regression, Random Forest y HistGradientBoosting.
- [x] Persistir el pipeline completo y sus metadatos con joblib.
- [x] Exponer CLI para entrenamiento, evaluación por temporada y predicción.
- [x] Añadir tests offline del filtrado temporal y del ciclo entrenamiento/predicción.

**Plan:** [`plan-ml-pipeline.md`](plans/plan-ml-pipeline.md:1).

### 20. Predicción operativa de la próxima jornada

- [x] Definir y validar el formato de `fixtures_next_round.csv` sin etiqueta.
- [x] Cortar estrictamente el histórico por `matchDate <= as_of`.
- [x] Construir snapshots prepartido para fixtures futuras usando el histórico enriquecido.
- [x] Añadir comando `next-round` que entrene/reentrene y prediga la próxima jornada.
- [x] Garantizar salida con fixture, `P(1)`, `P(X)`, `P(2)` y predicción.
- [x] Añadir tests anti-fuga: ningún partido posterior a `as_of` puede influir en una predicción.

**Plan:** [`plan-ml-pipeline.md`](plans/plan-ml-pipeline.md:1). Implementado.

## Bloque 8 — Optimización temporal de modelos

### 21. Selección de campeón con walk-forward y Optuna

- [x] Crear score combinado de `balanced_accuracy` y `log_loss`.
- [x] Implementar validación expanding/walk-forward por jornada.
- [x] Parametrizar los modelos existentes.
- [x] Añadir XGBoost y LightGBM como dependencias/modelos opcionales.
- [x] Implementar búsqueda Optuna con `MedianPruner`.
- [x] Persistir campeón, hiperparámetros y resultados del catálogo.
- [x] Añadir comando `tune` y smoke tests offline.
- [x] Hacer que `next-round` reutilice el campeón salvo `--retrain`.

**Plan:** [`plan-ml-optimizacion.md`](plans/plan-ml-optimizacion.md:1). Implementado.

## Posibles ampliaciones

- Evaluar la incorporación futura de variables de Europa y ascenso al contexto competitivo.
- Incorporar únicamente nuevas fuentes y variables cuando su cobertura, calidad, licencia y mantenimiento sean suficientes.