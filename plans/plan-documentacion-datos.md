# Plan: documentación de datos (bloque #13)

## Objetivo

Completar el bloque #13 de [`TODOS.md`](../TODOS.md:121): documentar fuentes, cobertura, columnas y limitaciones técnicas y legales.

## Contenido

Crear [`docs/datos.md`](../docs/datos.md:1) y enlazarlo desde [`README.md`](../README.md:1). Incluir:

1. **Fuentes:** BDFutbol (resultados) y Transfermarkt (valores de mercado y árbitros), con URLs base en [`Const.py`](../src/football_dataset/Const.py:1).
2. **Cobertura histórica:** temporadas 1970-71 hasta la última configurada; notas sobre temporadas sin datos.
3. **Frecuencia de actualización:** manual, bajo demanda de la CLI.
4. **Diccionario de columnas:** para cada columna de [`dataset_io.HEADERS`](../src/football_dataset/dataset_io.py:9), tipo, unidad y ventana temporal (cuando aplique).
5. **Variables derivadas:** descripción de posición, diferencia de puntos, rachas, forma y H2H, indicando explícitamente que solo usan datos previos.
6. **Limitaciones técnicas:** dependencia del HTML actual de las fuentes, posibilidad de `403/429`, valores de mercado ausentes representados como `-1`.
7. **Limitaciones legales:** respetar los términos de servicio de las fuentes y evitar scraping excesivo; mencionar el *rate limiting* aplicado.

## Cambios

- Crear [`docs/datos.md`](../docs/datos.md:1).
- Referenciar el diccionario de columnas desde [`README.md`](../README.md:1).
- Mantener [`dataset_io.HEADERS`](../src/football_dataset/dataset_io.py:9) como fuente de verdad única, con comentarios por columna.

## Criterios de aceptación

- Cada columna del CSV está documentada con tipo y unidad.
- Las limitaciones técnicas y legales están escritas.
- La documentación enlaza correctamente con las rutas reales del proyecto.