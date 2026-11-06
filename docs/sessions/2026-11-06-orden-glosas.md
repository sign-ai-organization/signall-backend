# El orden de las glosas, después del modelo

- **Fecha:** 2026-11-06
- **Rama:** `fix/fases1-3` (backend)
- **Base:** el arreglo de la capa de vocabulario (`0748898`) y el prompt sin tocar.
- **Qué se buscaba:** las frases donde el modelo acierta las glosas pero las pone en otro
  orden (`NIÑO,TRABAJAR,TODOS`, `QUIEN,VIVIR,TU,FAMILIA`).

## La convención del corpus, contada en las 120 frases

Antes de escribir una regla se miraron todas las glosas de referencia de FR-01 (30) y
FR-02 (90) con la categoría semántica de cada glosa, que ya está en `catalog`:

- **Pregunta con palabra interrogativa y verbo: el verbo va al final.** 8 de 8 casos.
  `DONDE TU FAMILIA VIVIR`, `CUANDO USTEDES COMER`, `QUIEN USTEDES COMER`.
- **`TODOS`/`TODAS` va pegado al sustantivo, antes del verbo.** 11 de 11 casos.
  `NIÑO TODOS TRABAJAR`, `GRACIAS TODOS`.
- **Las afirmaciones no tienen una convención única.** El verbo va antes de su complemento
  en casi todas (`ABUELO TIO VIVIR FAMILIA`, `USTEDES TRABAJAR FAMILIA`), pero mover un
  sustantivo de delante del verbo a detrás no se puede hacer sin saber si es sujeto o
  complemento: `ABUELO TIO VIVIR` no tiene complemento y la regla se equivocaría. Por eso
  no se toca ninguna afirmación.

## Lo que se agregó

`normalize_order(glosses, categories)` en `app/nlp/gloss_lexicon.py`, al final de
`LLMClient._repair_glosses`:

- Si la primera glosa es interrogativa y hay **un solo** verbo, el verbo se mueve al final.
  Con dos verbos no se toca: no hay caso en el corpus y adivinar sería peor.
- Si un `determinante` (`TODOS`) quedó detrás del verbo, vuelve justo antes de él.

Solo **mueve** glosas que el modelo ya produjo: no agrega, no quita y no reescribe.
Necesita las categorías del catálogo, así que `CatalogRepository` ganó `categories()`
(folded → categoría) y `LLMClient` recibe ese mapa como parámetro opcional. Sin categorías
—los tests viejos— la capa no hace nada.

## Medición

Prompt sin cambios. Caché vacía antes de cada corrida.

| Conjunto | Antes | Con el orden |
|---|---|---|
| FR-01 (30 frases) | 22-24 | **25** y **25** |
| FR-02 (90 frases) | 70-71 | **75** y **75** |

Sube en los dos y se repite igual, que es lo que el prompt no lograba: el prompt movía el
acierto de un conjunto al otro.

Las frases que arregla son las que la convención predice: `FR-01-027`
(`NIÑO,TRABAJAR,TODOS` → `NIÑO,TODOS,TRABAJAR`) y las preguntas de FR-02 con el verbo
delante del sujeto (`QUIEN,VIVIR,TU,FAMILIA` → `QUIEN,TU,FAMILIA,VIVIR`). No rompió
ninguna en las dos corridas.

## Lo que sigue fallando

- **FR-01-006:** el modelo omite `CON` y `GUSTO` solo no está en el catálogo. Es del
  modelo.
- **FR-01-013:** dice `LLAMAR` donde el corpus espera `NOMBRE`, y a veces `YO` en lugar de
  `TU`. Del modelo.
- **FR-01-010 y 024, FR-02-028/029/030:** el `TU` de la persona ambigua (decisión del
  owner) aparece una vez por oración y la referencia lo pone una sola vez por frase.
  Es la política, no el modelo.
- **FR-02-023:** «¿Estás contento?» se confunde con «¿Cómo estás?» de forma intermitente.
- **Afirmaciones con el verbo al final** (`USTEDES,FAMILIA,VIVIR`): la regla no las toca
  a propósito.

## Estado

- Commit con la capa de orden y sus tests.
- Backend reconstruido; la app instalada apunta a `ws://127.0.0.1:8080`.
