# `normalize_gloss` al dominio — TRA-01 pasa

- **Fecha:** 2026-11-10
- **Rama:** `fix/glosado-hue-cac-llm-p1` (la del PR #13)
- **Qué pedía:** PR-TRA-01 estaba en **Falla** desde el 2026-11-06 y otra vez el
  2026-11-10, con la misma causa: de 6 aristas entre los cuatro componentes del
  SDD, 2 se saltaban la interfaz.
- **Decisión del owner:** mover la función a un módulo neutral, no cambiar el
  criterio de la prueba.

## 1. Las dos aristas que fallaban

Las dos eran la misma importación, desde dos lugares:

| Desde | Hacia | Símbolo |
|---|---|---|
| `app/nlp/gloss_lexicon.py` | `app.validation.catalog_repository` | `normalize_gloss` |
| `app/nlp/llm_client.py` | `app.validation.catalog_repository` | `normalize_gloss` |

`normalize_gloss` dobla una glosa a la clave con la que los dos lados de una
búsqueda coinciden: mayúsculas, tildes, signos de interrogación y puntuación
se van, y la Ñ se queda. La regla la usaba el NLP para reparar lo que devuelve
el modelo y el catálogo para buscar la entrada.

## 2. El arreglo

La función y sus dos tablas de traducción pasaron a `app/domain/gloss_text.py`,
y los tres módulos que la usan importan desde ahí.

**Por qué el dominio:** es la capa que los dos componentes ya comparten
(`app/nlp/models.py` importa `PhraseType` de `app.domain.models`, y
`app/validation/catalog_repository.py` importa `CatalogEntry` de ahí). La regla
de cómo se escribe canónica una glosa es del dominio, no de la validación: el
NLP la necesita antes de que exista un catálogo que la haya buscado.

**Por qué no cambia el criterio:** la función es pura —sin estado, sin base de
datos, sin asincronía—, así que importarla no arrastra ninguna
implementación. El criterio de PR-TRA-01 ("ninguna importación debe saltarse la
interfaz") se cumple sin tocarlo.

`catalog_repository` sigue importando `normalize_gloss`, así que el nombre
queda disponible en su módulo y ningún otro archivo del repositorio cambia.

## 3. Cómo se verificó

- Los seis scripts de verificación del backend pasan
  (`verify_catalog_normalization`, `verify_catalog_synonyms`,
  `verify_gloss_lexicon`, `verify_llm_prompt`, `verify_gloss_analyzer`,
  `verify_static_analysis`).
- El arnés de PR-TRA-01 (`docs/plan-pruebas/arnes/tra01.py` en
  `sign-ai-android`), que lee solo el AST: **4 aristas, 4 por interfaz, 0 que
  se saltan la interfaz**. La evidencia es
  `PR-TRA-01_E_20261110_02.*`.
- Traducción real por el WebSocket contra el contenedor: «hola, buenos dias»
  devuelve `HOLA` y `BUENOS DIAS`, las dos con `available: true`.

## 4. Lo que falta del otro lado

El SDD no nombra esta función ni en la narrativa ni en los diagramas, así que
**no hay que tocarlo**: el cambio quedó anotado en `docs/sdd-changes.md` para
que quede escrito, y el diagrama de clases tampoco cambia (la función no es
una clase).

## 5. Una nota sobre las ramas

`develop` está 22 commits atrás de `main`: el PR #12 (recuperación de base de
datos) se fusionó a `main` y nunca llegó a `develop`. Por eso el PR #13, que
apunta a `develop`, se lleva dentro todo `main`. Conviene decidir si `develop`
se pone al día o si la rama de integración real es `main`.
