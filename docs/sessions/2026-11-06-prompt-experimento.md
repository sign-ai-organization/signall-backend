# El prompt: tres intentos, dos conjuntos y una decisión pendiente

- **Fecha:** 2026-11-06
- **Rama:** `fix/fases1-3` (backend)
- **Base:** la Fase 5 (`d95bfde`) y el ajuste del pronombre (`1ecc2e9`).
- **Qué se buscaba:** las 6 frases de FR-01 que no coincidían después del ajuste del
  pronombre, atacando el glosado y no la capa de vocabulario.

## 1. Tres de esas seis no eran del modelo

Antes de tocar el prompt se comparó, frase por frase, la respuesta cruda del modelo con la
respuesta reparada. Tres de las seis no las falla el modelo:

| Frase | Modelo | Reparado | Esperado |
|---|---|---|---|
| 006 | `NIÑOS, NIÑAS, COMER, GUSTO` | `NIÑO, NIÑO, COMER` | `NIÑO, NIÑA, COMER, CON GUSTO` |
| 016 | `POR QUE, ESTAS, TRISTE` | `TU, POR QUE, TRISTE` | `POR QUE, TU, TRISTE` |
| 027 | `NINOS, TRABAJAR, TODOS` | `NIÑA, TRABAJAR, TODOS` | `NIÑO, TODOS, TRABAJAR` |

- **`NIÑAS → NIÑO` y `NINOS → NIÑA` eran un bug de orden.** `_inflection_candidates`
  devolvía un `set`; como el catálogo tiene NIÑO y NIÑA, el resultado dependía de
  `PYTHONHASHSEED`. Comprobado con cinco semillas: la misma frase salía NIÑO en una y NIÑA
  en otra, y por eso dos corridas seguidas no coincidían.
- **El `TU` se insertaba al principio**, no después de la palabra de pregunta.
- **«COMO ESTAS» ya lleva la persona**, y se le agregaba un `TU` delante.

Arreglado en `app/nlp/gloss_lexicon.py`, con tres tests nuevos. Commit `0748898`.

Medición con el prompt sin cambios, dos corridas: **23/30 y 22/30** (112-113 glosas). La
tercera, con el arnés directo, 24/30. El rango es 22-24 porque el modelo confunde «¿Estás
triste?» con «¿Cómo estás?» de forma intermitente.

## 2. El prompt: lo que se probó y lo que costó

La pregunta era si un prompt distinto podía cerrar 006 (`CON GUSTO`), 013 (`NOMBRE`) y
029 (`SENTIR` de más). Se probaron cuatro variantes, cada una con repetición por frase,
y después las dos mejores sobre FR-02 completo (90 frases que **no** están en el prompt).

**Reescritura agresiva** (orden de la pregunta, sustantivos en singular, la persona
antes del verbo, «una pregunta sobre el nombre se responde con NOMBRE»): **22/30**. Arregló
006, 013 y 029 y rompió 004, 009, 012, 018 y 028. El modelo empezó a inventar `POR QUE`
en preguntas de sí/no y en «porque», singularizó `PERSONAS` a `PERSONA` (que no está en el
catálogo) y movió `TIO` delante de `TRABAJAR` en «Trabaja con el tío».

**Por regla suelta, seis corridas por frase:**

| Regla | 006 | 013 | 018 | 029 |
|---|---|---|---|---|
| «la frase fija mantiene su preposición» | 6/6 | — | 6/6 | — |
| «un saludo es una sola glosa» | — | — | 6/6 | 6/6 |
| «se responde con la cosa» (genérica) | 4/6 | 6/6 | **0/6** | 0/6 |
| ejemplo «¿Cómo se llama usted? → COMO,USTED,NOMBRE» | — | 6/6 | 6/6 | — |

La regla genérica del nombre es la que rompía 018: el modelo tiraba `PERSONAS` y `QUE`
como si no fueran «la cosa». El ejemplo hace el mismo trabajo y no generaliza igual.

**La versión final probada** (el prompt viejo + la regla de la frase fija + la del saludo +
el ejemplo del nombre) dio **26/30 en tres corridas seguidas** por el WebSocket, 114/112
glosas. Ese es el número que el plan pedía (26-28).

## 3. La validación en FR-02 dice que no

FR-02 tiene 90 frases con glosas de referencia, construidas con las mismas convenciones y
**fuera** del prompt. Mismo código, mismos dobles, misma reparación:

| Prompt | FR-01 | FR-02 | Total (120) |
|---|---|---|---|
| El de siempre | 22-24 | 70-71 | ~94 |
| + frase fija + saludo + ejemplo del nombre | **26** | **67-69** | ~94 |

Sobre 120 frases queda igual. El prompt mueve el acierto de un conjunto al otro: gana 3 en
FR-01 y pierde 3 en FR-02. Las frases que rompe en FR-02 son concretas y repetibles:

- **004** `Hola a todos. Buenos días.` → se pierde `TODOS` (la regla del saludo trata
  «Hola a todos» como un saludo entero).
- **019** `¿Tienes sed?` → el modelo dice `TENER,SED`, dos glosas fuera del catálogo.
- **020, 023, 031, 032** `¿Estás triste?`, `¿Estás contento?` → el modelo agrega `COMO`,
  arrastrado por los dos ejemplos que empiezan con «¿Cómo…?».
- **004, 020, 021, 031, 073, 074, 087** también aparecen al probar **solo** la regla de la
  frase fija (65/90): no es que una regla sea la mala; cualquier cambio al prompt perturba
  frases que hoy salen bien por casualidad.

## 4. Lo que tampoco arregla

- **`gpt-4o` con el prompt de siempre:** FR-01 25/30, FR-02 71/90. Lo mismo que
  `gpt-4o-mini`. No es capacidad del modelo.
- **Quitar la rama ambigua del pronombre** («se siente mal» → TU): FR-01 23/30, FR-02
  73/90. Mueve una frase de un conjunto al otro, igual que el prompt.

Lo que queda fallando es, sobre todo, **orden** (`NIÑO,TODOS,TRABAJAR` contra
`NIÑO,TRABAJAR,TODOS`; `QUIEN,TU,FAMILIA,VIVIR` contra `QUIEN,VIVIR,TU,FAMILIA`), la
duplicación de `TU` entre oraciones y `NOMBRE` en FR-01-013. Son convenciones del corpus
que el modelo no sigue de forma estable, no un problema del pipeline.

## 5. Estado

- El arreglo de `gloss_lexicon.py` está commiteado y subido (`0748898`).
- **El prompt quedó como estaba.** Se probó, se midió y se revirtió: no mejora el sistema,
  solo mueve el error. El texto de la versión que daba 26/30 está en el historial de esta
  sesión y se puede reponer en un minuto si el owner prefiere el número de FR-01 y reportar
  el costo en FR-02 al lado.
- El backend corre el prompt de siempre, con 63 glosas y la caché vacía al cerrar.
