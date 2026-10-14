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

## Bloque 9 — Ingeniería de features avanzadas

### 22. Features temporales, casa/fuera y rendimiento relativo

- [x] Añadir dinámica de goles local/visitante con medias móviles 5 y 10.
- [x] Añadir rachas específicas de casa/fuera y número de partidos disponibles.
- [x] Añadir días de descanso, partidos en los últimos 7 días y diferencia de descanso.
- [x] Añadir sobre-rendimiento relativo al valor de mercado.
- [ ] Migrar el esquema fuente a v4 si se decide persistir estas columnas en el CSV histórico.
- [x] Incluir las nuevas features de forma determinista en `ml_features.py`.
- [x] Mantener paridad de features para snapshots de fixtures futuras.
- [x] Añadir tests de no fuga temporal para las nuevas features.

**Plan:** [`plan-features-avanzadas-ml.md`](plans/plan-features-avanzadas-ml.md:1).

### 23. Estrategia de target y modelos avanzados

- [x] Implementar clasificador de dos etapas empate/ganador en [`staged.py`](src/football_ml/staged.py:1).
- [x] Implementar modelo Poisson de goles y derivación 1X2 en [`poisson.py`](src/football_ml/poisson.py:1).
- [ ] Añadir early stopping a XGBoost y LightGBM.
- [ ] Implementar umbral calibrado para la clase empate.
- [ ] Ajustar trials por modelo y priorizar modelos rápidos.
- [x] Explorar ventanas recientes 4/5/8/12 temporadas con `compare`.
- [ ] Ejecutar comparación completa sobre un holdout temporal intocable y seleccionar campeón.

**Plan:** [`plan-estrategia-target-ml.md`](plans/plan-estrategia-target-ml.md:1).

## Posibles ampliaciones

- Evaluar la incorporación futura de variables de Europa y ascenso al contexto competitivo.
- Incorporar únicamente nuevas fuentes y variables cuando su cobertura, calidad, licencia y mantenimiento sean suficientes.