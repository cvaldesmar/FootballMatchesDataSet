# Football Matches DataSet

Generador de datasets de partidos de fútbol de Primera y Segunda División española, con datos históricos, clasificación acumulada y enriquecimiento opcional mediante valores de mercado y árbitros.

## Arquitectura

La implementación principal está organizada como paquete en [`src/football_dataset/`](src/football_dataset):

El backlog de trabajo vive en [`TODOS.md`](TODOS.md:1); cada elemento pendiente tiene su plan de implantación en [`plans/`](plans/README.md:1).

- [`Main.py`](src/football_dataset/Main.py): CLI y orquestación del proceso.
- [`DatosTemporada.py`](src/football_dataset/DatosTemporada.py): reconstrucción de la clasificación y creación de partidos.
- [`FootballClasses.py`](src/football_dataset/FootballClasses.py): modelos [`Equipo`](src/football_dataset/FootballClasses.py:8) y [`Partido`](src/football_dataset/FootballClasses.py:27).
- [`WebScraper.py`](src/football_dataset/WebScraper.py): lectura de temporadas desde BDFutbol.
- [`FileScraper.py`](src/football_dataset/FileScraper.py): lectura de temporadas desde CSV.
- [`MarketHelper.py`](src/football_dataset/MarketHelper.py): valores de mercado de Transfermarkt.
- [`RefereesHelper.py`](src/football_dataset/RefereesHelper.py): árbitros y resultados de Transfermarkt.
- [`UtilsAndGlobals.py`](src/football_dataset/UtilsAndGlobals.py): utilidades puras de normalización y resolución de equipos.
- [`Const.py`](src/football_dataset/Const.py): URLs, temporadas y equivalencias de nombres.

El flujo de datos es:

```text
CLI -> ExecutionContext -> DatosTemporada -> WebScraper/FileScraper -> parsers
                                      -> MarketHelper/RefereesHelper -> parsers
                                      -> DatasetValidator -> CSV de salida
```

### Capas de fiabilidad

- [`http_client.py`](src/football_dataset/http_client.py:1) centraliza `requests` con timeout obligatorio, reintentos con backoff, rate limiting y errores explícitos para 403, 404, 429 y 5xx.
- [`parsers/`](src/football_dataset/parsers) contiene parsers puros y validables para BDFutbol y Transfermarkt. El parser CSV se encuentra en [`csv_parser.py`](src/football_dataset/parsers/csv_parser.py:1); un cambio de estructura produce [`ParserError`](src/football_dataset/parsers/errors.py:1) descriptivo.
- [`context.py`](src/football_dataset/context.py:1) contiene [`ExecutionContext`](src/football_dataset/context.py:10), creado por cada ejecución; no se reutilizan registros ni contadores globales.
- [`validation.py`](src/football_dataset/validation.py:1) genera `QualityReport` antes de persistir y detecta duplicados, equipos desconocidos, marcadores inconsistentes, fechas/jornadas inválidas y conteos inesperados. El umbral se configura con `--max-errors`.
- El CSV incluye variables históricas previas al partido: puntos, goles acumulados, posición (`posicionLocal`/`posicionVisitante`) y diferencia de puntos (`diferenciaPuntos`). La tabla se congela al inicio de cada jornada para evitar fuga de información intra-jornada.
- También incluye forma reciente (`rachaLocal`/`rachaVisitante`, `formaLocal`/`formaVisitante`) y enfrentamientos directos (`h2hLocalWins`, `h2hDraws`, `h2hAwayWins`, `h2hMatches`). Se calculan con una ventana máxima de cinco partidos anteriores y con snapshots por jornada para evitar fuga de información.
- El contexto competitivo previo incluye `campeonId`, descenso matemáticamente confirmado para local/visitante (`descensoConfirmadoLocal`/`descensoConfirmadoVisitante`) y presión competitiva (`presionLocal`/`presionVisitante`) en escala `0..3`. Por ahora se omiten Europa y ascenso.
- La flag `rivalidad` (0/1) marca partidos de rivalidades clásicas vigentes (clásico, derbis territoriales, etc.), incluida también en el CSV.
- [`dataset_io.py`](src/football_dataset/dataset_io.py:1) exporta el CSV recibiendo el contexto explícitamente. Todas las columnas generadas por los bloques #8, #9, #10 y #15 se escriben en el fichero de salida para su uso posterior en aprendizaje automático.

## Tests y calidad de código

La suite determinista se ejecuta sin red:

```bash
python -m pytest -q
```

Las herramientas de desarrollo se instalan junto con [`requirements.txt`](requirements.txt:1). El proyecto usa [`ruff`](https://docs.astral.sh/ruff/) para linting y formateo, y [`mypy`](https://mypy-lang.org/) para comprobación estática de tipos. El chequeo estricto de mypy se aplica actualmente al módulo nuevo [`persistence.py`](src/football_dataset/persistence.py:1); la adopción del resto de módulos históricos está planificada progresivamente para evitar ocultar errores con una exclusión global:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Para aplicar automáticamente el formateo de Ruff:

```bash
python -m ruff format .
```

La integración continua está definida en [`.github/workflows/ci.yml`](.github/workflows/ci.yml:1). Se ejecuta en cada push y pull request sobre Python 3.11 y 3.12, y verifica linting, formato, tipos y tests offline. Las pruebas de integración externa siguen excluidas por defecto.

Los tests contra las fuentes reales están marcados como `integration`:

```bash
python -m pytest -q -m integration -o addopts=
```

Un `403`, `429` o indisponibilidad temporal de una fuente externa se muestra como `skip`, no como un falso fallo de regresión. La suite offline siempre queda activa por defecto.

## Auditoría independiente de datasets

La auditoría offline está implementada en [`audit.py`](src/football_dataset/audit.py:1) y se valida automáticamente mediante [`test_audit_dataset.py`](tests/test_audit_dataset.py:1). Comprueba metadatos, columnas obligatorias, etiquetas `1/X/2`, duplicados, identidad local/visitante, tipos numéricos, huecos entre jornadas y consistencia interjornada. En el dataset fuente usa `idPartido`; en el dataset ML usa la clave `division + temporada + jornada + localId + visitanteId`.

Para obtener un informe manual opcional:

```bash
python -m src.football_dataset.audit --input data/dataset_ml.csv --format text
python -m src.football_dataset.audit --input data/dataset_ml.csv --format json
```

En la auditoría actual del dataset ML se detectan 43.884 filas, distribución `1=21.794`, `X=12.165`, `2=9.925`, ningún error estructural y 7.074 distancias desconocidas (`-1`). El CSV ML no incluye `idPartido` por diseño, así que la auditoría de duplicados por partido se realiza sobre el dataset fuente, no sobre el artefacto simplificado.

## Dataset derivado para Machine Learning

El CSV histórico/enriquecido es la fuente de verdad y no se sobrescribe al generar features. El módulo [`ml_features.py`](src/football_dataset/ml_features.py:1) produce un artefacto derivado simplificado para el pronóstico multiclase `resultado1X2`:

```bash
python -m src.football_dataset.ml_features --input data/dataset_historico_1970_2025_enriquecido.csv --output data/dataset_ml.csv
```

La transformación es offline y determinista. Conserva las variables numéricas útiles, elimina identificadores y texto crudo y mantiene `resultado1X2` como etiqueta. Además de las diferencias básicas, genera features avanzadas exclusivamente con snapshots anteriores: medias móviles de goles a favor/en contra a 5 y 10 partidos, rendimiento específico en casa/fuera, días de descanso, carga de partidos en 7 días y sobre-rendimiento frente al valor de mercado.

Estas features avanzadas se calculan en el artefacto ML derivado y no modifican el CSV histórico fuente v3. La migración del esquema persistente a v4 queda separada para evitar invalidar datasets históricos existentes.

Durante una generación completa también puede solicitarse el artefacto derivado con `--build-ml` y `--ml-output`.

### Pipeline de entrenamiento ML

El modelado vive separado del generador en [`src/football_ml/`](src/football_ml). Sus dependencias opcionales están en [`requirements-ml.txt`](requirements-ml.txt:1), para no añadir `pandas` y `scikit-learn` al entorno básico de scraping:

```bash
python -m pip install -r requirements-ml.txt
```

El pipeline trata el histórico como una serie temporal. Por defecto descarta las temporadas anteriores a `2000-01`; también puede conservar únicamente las últimas `N` temporadas. El filtro se aplica antes del preprocesado y se registra en el modelo persistido:

```bash
python -m src.football_ml train --input data/dataset_ml.csv --min-season 2000-01 --model data/model.joblib --model-name logistic
python -m src.football_ml train --input data/dataset_ml.csv --last-seasons 15 --model data/model.joblib --model-name random-forest
```

Después del recorte, las temporadas se separan cronológicamente: las antiguas para entrenamiento, una o más para validación y las más recientes como test. No se barajan temporadas. El modelo persistido contiene el pipeline de preprocesado, el clasificador, las temporadas utilizadas y las métricas.

### Predicción operativa de la próxima jornada

El fichero [`data/dataset_ml.csv`](data/dataset_ml.csv) actual es histórico y está completamente etiquetado: contiene 43.884 partidos finalizados, de `1970-71` a `2025-26`. No contiene partidos futuros de `2026-27` ni filas sin `resultado1X2`.

Para predecir la siguiente jornada hay que proporcionar un calendario futuro sin resultados, por ejemplo `data/fixtures_next_round.csv`:

```text
;division;temporada;jornada;matchDate;localId;visitanteId
;1;2026-27;8;2026-10-18;123;456
```

El comando [`next-round`](src/football_ml/__main__.py:39) realiza el flujo completo:

1. corta el histórico enriquecido con `matchDate <= as_of`;
2. descarta temporadas antiguas según `--last-seasons` o `--min-season`;
3. entrena con resultados ya conocidos;
4. reconstruye clasificación, forma, H2H y diferencias para cada fixture futura;
5. devuelve `P(1)`, `P(X)`, `P(2)` y la predicción.

Ejemplo para el caso indicado:

```bash
python -m src.football_ml next-round --history data/dataset_historico_actualizado_enriquecido.csv --fixtures data/fixtures_next_round.csv --model data/model_2026-10-14.joblib --as-of 2026-10-14 --last-seasons 10 --output data/predicciones_jornada.csv
```

La fixture debe ser posterior a `as_of` y no puede contener goles ni `resultado1X2`. El histórico sí debe estar actualizado con todos los partidos disputados hasta la fecha de corte. Si solo se dispone del CSV actual hasta `2025-26`, no se puede realizar correctamente una predicción de la jornada de octubre de `2026-27`.

Para evaluar o predecir:

```bash
python -m src.football_ml evaluate --input data/dataset_ml.csv --model data/model.joblib --by-season
python -m src.football_ml predict --model data/model.joblib --input data/partidos_futuros.csv --output data/predicciones.csv
```

La métrica principal es `log_loss`, complementada con `balanced_accuracy`, `macro-F1`, matriz de confusión y métricas por clase. Las columnas identificadoras de equipo y temporada se usan para trazabilidad/split, no como features crudas. Los `-1` de distancia y mercado se tratan como ausencia explícita; los `-1` que representan diferencias deportivas legítimas no se imputan.

### Comparación preliminar de estrategias

El subcomando `compare` evalúa multiclase directo, staged y Poisson con las mismas rondas walk-forward. En una exploración corta de 10 rondas, Poisson obtuvo el mejor `combined_score` en todas las ventanas probadas: 4 temporadas (`-0.570`), 5 (`-0.551`), 8 (`-0.565`) y 12 (`-0.487`). También obtuvo el mejor `log_loss` (1.003–1.058). Estos resultados son preliminares: todavía debe ejecutarse una validación completa sobre un holdout temporal intocable y optimizar hiperparámetros antes de elegir el campeón operativo.

Como estrategias alternativas están implementados [`Staged1X2Classifier`](src/football_ml/staged.py:14), que modela empate/no empate y ganador, y [`Poisson1X2Classifier`](src/football_ml/poisson.py:14), que ajusta goles locales/visitantes y deriva las probabilidades 1X2. Ambos están integrados en el comando `compare` y validados con tests de coherencia de probabilidades; todavía debe ejecutarse una validación completa sobre holdout antes de seleccionar uno como campeón operativo.

### Optimización de modelos e hiperparámetros

Para buscar el mejor modelo no se utiliza un `train_test_split` aleatorio. El comando [`tune`](src/football_ml/__main__.py:42) ejecuta validación *walk-forward*: agrupa los partidos por `(temporada, jornada)`, entrena con todas las jornadas anteriores y valida sobre la siguiente. Optuna explora hiperparámetros de regresión logística, Random Forest, HistGradientBoosting, XGBoost y LightGBM, con `MedianPruner` para detener configuraciones poco prometedoras.

```bash
python -m src.football_ml tune --input data/dataset_ml.csv --last-seasons 12 --models logistic random-forest gradient-boosting xgboost lightgbm --trials-per-model 50 --min-train-rounds 10 --model data/campeon.joblib
```

La selección usa `balanced_accuracy - log_loss / ln(3)`: considera las tres clases y la calidad de las probabilidades. El artefacto guarda el modelo campeón, parámetros, score walk-forward y resultados de cada modelo. La búsqueda es una operación periódica; no se ejecuta automáticamente cada jornada.

El ciclo recomendado es:

1. actualizar el histórico hasta la fecha de corte;
2. ejecutar `tune` cuando haya suficiente información nueva o al inicio de temporada;
3. usar el `campeon.joblib` generado para cada `next-round`;
4. reoptimizar posteriormente y comparar contra el campeón anterior.

## Ejecución

El lanzador compatible de la raíz sigue funcionando:

```bash
python Main.py --latest
```

También puede ejecutarse el paquete directamente:

```bash
python -m src.football_dataset --latest
python -m src.football_dataset --seasons 2021-22 2022-23 --divisions 1 2 --output dataset.csv
python -m src.football_dataset --from-file --input-file TestSave.csv --output dataset.csv
```

Por defecto se procesan las temporadas cortas configuradas en [`Const.py`](src/football_dataset/Const.py:10). Consulta todas las opciones con:

```bash
python Main.py --help
```

## HTTP y fuentes externas

Las peticiones a BDFutbol y Transfermarkt usan el mismo cliente HTTP. El cliente aplica una pausa mínima entre peticiones y reintenta errores transitorios; los errores permanentes se exponen como [`HttpError`](src/football_dataset/http_client.py:12). Las pruebas reales no deben ejecutarse con frecuencia excesiva: respetar los límites y condiciones de uso de las fuentes.

## Logging

El proyecto ya no modifica `builtins.print`. El paquete usa el módulo estándar [`logging`](https://docs.python.org/3/library/logging.html), con formato:

```text
fecha | nivel | módulo | mensaje
```

Los mensajes operativos se registran con niveles `INFO`, `WARNING` y `ERROR`. La salida de la CLI que representa resultados finales conserva `print` explícito y localizado en el punto de entrada.

## Cachés y esquema persistente

Las cachés nuevas son JSON legible y versionado:

- `market_values.json`: valores por división y fecha.
- `referees.json`: árbitros por temporada, división y partido.

Cada archivo contiene `version: 2`. El guardado es atómico: se escribe un temporal en el mismo directorio, se fuerza a disco y se publica con `os.replace`, evitando dejar una caché parcialmente escrita. La carga rechaza JSON corrupto y versiones desconocidas mediante errores tipados; las migraciones entre versiones se registran explícitamente en [`persistence.py`](src/football_dataset/persistence.py:1). Las fechas se guardan en formato ISO `YYYY-MM-DD`; no se ejecuta deserialización arbitraria como ocurría con `pickle`. Las rutas pueden cambiarse con `--market-cache` y `--referees-cache`.

El CSV incluye el metadato `# football_dataset_schema=1` antes de su cabecera. [`dataset_io.py`](src/football_dataset/dataset_io.py:1) valida ese metadato y el orden exacto de columnas al reanudar una exportación incremental, evitando mezclar esquemas incompatibles. Las futuras versiones deben añadir una migración documentada antes de aceptarse.

Los archivos `.pickle` antiguos y las copias de respaldo no forman parte del flujo de ejecución y se han eliminado de la estructura activa del proyecto.

## Generación local de datasets históricos

Las generaciones grandes se ejecutan localmente y escriben sus artefactos en [`data/`](data:1), que está excluido de Git. El comando recomendado para el histórico completo de ambas divisiones es:

```bash
python -m src.football_dataset --all --divisions 1 2 --output data/dataset_historico_1970_2025.csv --market-cache data/market_values_historico.json --referees-cache data/referees_historico.json --log-file data/generacion_historico.log
```

Para reanudar una ejecución interrumpida sin repetir temporadas ya presentes en el CSV:

```bash
python -m src.football_dataset --all --divisions 1 2 --resume --output data/dataset_historico_1970_2025.csv --market-cache data/market_values_historico.json --referees-cache data/referees_historico.json --log-file data/generacion_historico.log
```

`--resume` valida el esquema del CSV, detecta los pares `division/temporada` ya escritos y omite únicamente esos pares. `--log-file` conserva el detalle de inicio, finalización y omisión de cada temporada, incluso cuando la consola no está disponible. La ejecución utiliza [`append_season()`](src/football_dataset/dataset_io.py:56), por lo que cada temporada completada queda persistida antes de comenzar la siguiente.

### Enriquecimiento offline

El CSV histórico puede conservarse como fuente base y enriquecerse posteriormente sin volver a descargar ni parsear BDFutbol. El módulo [`enrichment.py`](src/football_dataset/enrichment.py:1) ofrece dos operaciones:

1. Descargar una vez las cachés de Transfermarkt usando el CSV histórico para conocer divisiones, fechas y partidos:

```bash
python -m src.football_dataset.enrichment --input data/dataset_historico_1970_2025.csv --market-cache data/market_values_historico.json --referees-cache data/referees_historico.json --download-caches
```

2. Crear un nuevo CSV enriquecido usando exclusivamente el CSV y las cachés locales:

```bash
python -m src.football_dataset.enrichment --input data/dataset_historico_1970_2025.csv --market-cache data/market_values_historico.json --referees-cache data/referees_historico.json --enrich-output data/dataset_historico_1970_2025_enriquecido.csv
```

La segunda operación no usa red. Conserva todas las columnas deportivas, completa `localMarketValue`, `visitanteMarketValue`, `arbitroName` y `arbitroId`, y mantiene el metadato de esquema. El CSV base no se modifica, por lo que puedes repetir el enriquecimiento con nuevas versiones de las cachés y comparar resultados.

Antes de consumir el resultado en el proyecto de machine learning, conviene conservar junto al CSV el commit del código, el comando utilizado, la versión del esquema y el informe de validación.

## Dependencias

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

## Estructura actual

La raíz contiene únicamente el lanzador compatible [`Main.py`](Main.py:1), configuración, documentación y datos de entrada de referencia. La implementación única está en [`src/football_dataset/`](src/football_dataset); no existen copias paralelas de los módulos de aplicación.

Los recursos históricos y ejemplos HTML se mantienen en [`Varios/`](Varios/README.md).
