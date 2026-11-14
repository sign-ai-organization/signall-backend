# SonarQube en cero y cobertura real

- **Fecha:** 2026-11-14
- **Repo:** `signall-backend`
- **Qué pedía:** dejar el proyecto `signall-backend` de SonarQube local sin hallazgos y con
  cobertura distinta de 0 %.

## Resultado

| Medida | Antes | Después |
|---|---|---|
| Issues sin resolver | 6 (5 de complejidad cognitiva, 1 de tipo) | **0** |
| Cobertura | 0 % (sin reporte) | **82,8 %** de 1962 líneas |
| Code smells | 6 | **0** |
| Complejidad cognitiva total | 479 | 472 |

Medido con el escáner local contra `http://localhost:9000` (`api/issues/search`,
`api/measures/component`) el 2026-11-14, con el código de los commits `63b4a0a` y
`7bfff6c`. La cobertura sale de `scripts/cobertura.sh`, que corrió 22 scripts y dejó
`.coverage` con 1624 de 1962 líneas.

## Los seis hallazgos

Ninguno era un error de comportamiento: los seis eran funciones demasiado grandes. El
refactor fue extraer funciones con nombre, sin cambiar el orden de las condiciones, la
secuencia de estado ni los puntos donde se toma una métrica.

| Archivo | Función | Antes | Qué se extrajo |
|---|---|---|---|
| `app/persistence/recovery.py` | `recover_database` | 19 | `_recover_once`, `_open_pool`, `_load_catalog`, `_reload_cache` |
| `app/controller/router.py` | `_forward_audio` | 22 | `_handle_message`, `_handle_audio_fragment` |
| `app/nlp/segmenter/_clauses.py` | `split_by_clauses` | 73 | `_Clause`, `_FragmentState`, `_question_start`, `_subject_start`, `_extend_subject`, `_decide_cut`, `_blocks_cut`, `_process_word` |
| `app/nlp/segmenter/_discourse_markers.py` | `split_by_markers` | 38 | `_cut_after_closing`, `_cut_before_marker`, `_cut_before_interrogative`, `_cuts_here` |
| `app/nlp/segmenter/_post_processing.py` | `_merge_short` | 19 | `_merge_short_into_previous`, `_merge_short_into_next` |
| `app/orchestrator/orchestrator.py` | `translate` | S5864 | bucle `async for` explícito |

**El S5864 es un falso positivo.** La expresión original
(`[segment async for _, _, segment in self.translate_stream(text)]`) es una comprensión
asíncrona válida; el analizador la leyó como una iteración síncrona de un
`AsyncIterator`. El bucle explícito dice lo mismo con la forma que Sonar sí entiende, y
no cambia nada en tiempo de ejecución.

## Cómo se comprobó que no cambió el comportamiento

No alcanza con que los 191 casos del laboratorio sigan pasando, así que se comparó el
árbol anterior (`git archive HEAD`) contra el nuevo, corriendo los dos dentro de la imagen
del backend:

1. **`scripts/verify_sentence_segmenter.py`**: 191/191 casos idénticos al laboratorio.
2. **Corpus diferencial de 411 textos** (los 191 del fixture, 20 escritos a mano y 200
   recombinaciones con `y`, `pero`, `,`, `o sea` y `por favor`): salida idéntica. Este
   corpus encontró una diferencia real que el fixture no veía: en el recorrido del
   sujeto nominal, la posición de corte solo se mueve cuando aparece un interrogativo,
   un posesivo o una `y`, no hasta la última palabra recorrida. Con eso corregido, 0
   diferencias.
3. **Reglas de marcadores y post-proceso**: 9 configuraciones (las dos direcciones de
   fusión, `filler_policy` en `merge` y `discard`, post-proceso apagado, sin marcadores)
   por 22 textos: fragmentos idénticos.
4. **Nueve verify scripts** que tocan estos archivos (`sentence_segmenter`,
   `database_recovery`, `client_frames`, `turn_id`, `audio_validation`, `done_on_error`,
   `metrics_sources`, `endpoints`, `orchestrator_interface`): salida idéntica, con la
   misma lista de fallas que ya existía antes.

## Cobertura

`scripts/cobertura.sh` corre los `verify_*.py` bajo `coverage run --parallel-mode
--source=app`, combina y escribe `coverage.xml` en la raíz. `--source=app` cuenta como 0 %
los módulos que ningún script importó, que es el denominador honesto.

- **22 scripts corren**: no necesitan servicios.
- **6 se saltean con el motivo impreso**: `verify_catalog_repository`,
  `verify_validator_service` y `verify_semantic_cache` leen o escriben en Neon;
  `verify_nlp_service` y `verify_orchestrator` necesitan Neon, embeddings y LLM; y
  `verify_llm_client` llama al modelo y además pide entrada por teclado. Se incluyen con
  `SIGNALL_COBERTURA_SERVICIOS=1`. No se les puso un doble: un script que finge un
  servicio también finge sus fallas.
- `coverage` no está en la imagen del servicio; el runner lo instala en
  `/tmp/signall-cobertura-deps-<uid>` del host y lo monta, porque cada
  `docker compose run` es un contenedor nuevo.

## Pendiente que este trabajo no toca

Cuatro scripts fallan, y **ya fallaban antes** de este cambio (comprobado corriéndolos
sobre `git archive HEAD`):

`verify_audio_validation`, `verify_client_frames`, `verify_done_on_error` y
`verify_turn_id`.

La causa es que esperan los frames de antes de dos cambios del código: el frame
`capability` que entró con `8a31cc2` (`feat(session): keep the session open when the STT
is down`) y la traducción de la frase en su propia tarea, que llegó con `8631115`
(`fix(session): keep the read loop draining`). Los scripts leen el socket antes de que
llegue el `done`, así que comparan listas de frames incompletas. **No se arreglaron acá**:
son pruebas de un contrato que no se tocó en esta sesión y el arreglo mezcla dos cosas.
El runner los reporta como FALLA y produce igual el reporte; con
`SIGNALL_COBERTURA_ESTRICTO=1` termina con error para quien quiera usarlo como puerta.

## Cómo repetirlo

```bash
scripts/cobertura.sh          # deja coverage.xml
# y después el escáner, con el token de ~/.config/signall/sonar.env
```
