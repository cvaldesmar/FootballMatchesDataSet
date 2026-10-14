# Plan: rivalidades y partidos clásicos (bloque #15)

## Objetivo

Completar el bloque #15 de [`TODOS.md`](../TODOS.md:135): añadir una flag binaria `rivalidad` (1 si el partido tiene una rivalidad clásica vigente; 0 en otro caso) y exportarla al CSV.

## Decisión de formato

- Una única columna `rivalidad` de tipo entero `0`/`1`.
- No se añade etiqueta categórica. Para Machine Learning, la flag es suficiente como "termómetro" de que el partido tiene más enjundia que un partido normal.
- El indicador es simétrico: vale lo mismo si el local y el visitante se intercambian.

## Rivalidades incluidas

Se usan los nombres normalizados de [`Const.py`](../src/football_dataset/Const.py:16). Cada par se trata como conjunto no ordenado:

1. Real Madrid – Barcelona (El Clásico)
2. Real Madrid – Atlético de Madrid (derbi madrileño)
3. Barcelona – Espanyol (derbi barcelonés)
4. Sevilla – Betis (derbi sevillano)
5. Athletic Club – Real Sociedad (derbi vasco)
6. Celta de Vigo – Deportivo de La Coruña (derbi gallego)
7. Valencia – Villarreal (derbi de la Comunitat)
8. Oviedo – Sporting de Gijón (derbi asturiano)
9. Las Palmas – Tenerife (derbi canario)
10. Getafe – Leganés (derbi del sur de Madrid)

Se excluyen rivalidades históricas que hoy no tienen la misma carga (por ejemplo, Real Madrid – Valencia), siguiendo el criterio de "muy típicas y vigentes".

## Nota sobre el CSV de salida

Todas las variables generadas (incluidas las de este bloque y las de los bloques #8, #9 y #10) se escriben en el CSV de salida mediante [`save_all_seasons()`](../src/football_dataset/dataset_io.py:28) y su lista [`HEADERS`](../src/football_dataset/dataset_io.py:9). El objetivo del dataset es maximizar la información disponible para el posterior aprendizaje automático.

## Cambios

1. Añadir `RIVALRIES` en [`Const.py`](../src/football_dataset/Const.py:1) como conjunto de pares ordenados canónicos.
2. Añadir `rivalidad: int = 0` a [`Partido`](../src/football_dataset/FootballClasses.py:27), con coerción en `__post_init__`.
3. Calcularlo en [`DatosTemporada.addMatch()`](../src/football_dataset/DatosTemporada.py:97) comparando el par normalizado del partido contra `RIVALRIES`.
4. Añadir `rivalidad` a [`HEADERS`](../src/football_dataset/dataset_io.py:9).
5. Documentar en [`README.md`](../README.md:1) y [`TODOS.md`](../TODOS.md:135).

## Tests

- Un clásico conocido (Real Madrid – Barcelona) se marca `1`.
- Un partido sin rivalidad se marca `0`.
- La lista es simétrica (invertir local/visitante no cambia el valor).
- La columna `rivalidad` aparece en el CSV exportado.

## Estado

Implementado y validado. La flag binaria `rivalidad` se exporta al CSV junto con las variables de los bloques #8, #9 y #10. La suite offline pasa con 17 tests.

## Criterios de aceptación

- La flag es binaria y reproducible.
- La lista de rivalidades está documentada y es criterio de vigencia actual.
- La suite offline permanece verde.