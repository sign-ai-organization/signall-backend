# R-04 · El contrato con la app después del renombre a SignAll

- **Fecha:** 2026-11-13
- **Repos:** `signall-backend` y `signall-android`
- **Qué pedía:** el bloque R-04 del plan de reestructuración: "nombres que cruzan el
  WebSocket (`rt_*`, frames), en los dos lados el mismo día".
- **Decisión del owner:** `rt_*` y los frames **no** se renombran.

## Resultado

No hubo cambio de código en este repositorio. El bloque se hizo leyendo el contrato en
los dos lados y comprobando que **ninguna cadena que cruza el socket lleva la marca**:

| Qué | Estado |
|---|---|
| Frames app → backend | `text`, `end` y audio binario. Sin marca. |
| Frames backend → app | `transcript`, `segment`, `done`, `error`, `capability`, más `trace`/`sentence_trace` de depuración. Sin marca. |
| Nombres de métrica | `rt_*` en `/metrics`. El prefijo es de "tiempo real", no de la marca. |
| Identificadores de datos | `signs/<id>.glb`, clips `0000_afirmativo`..`0049_orden`, glosas `GLS-*`. Son contrato y no se tocan. |

Renombrar los `rt_*` habría invalidado la comparación con la línea base publicada
(913 ms p50 / 1336 ms p95) y con lo que citan el SRS y el SDD, sin ganar nada: el
número no dice la marca.

Lo único que cambió de nombre es del lado del teléfono y no cruza el socket:
`SignAiMetrics` → `SignAllMetrics` (bloque R-03 de android, commit `cf9fb5b`). El
backend nunca supo cómo se llama esa clase.

## Comprobaciones

- `app/controller/controller.py:315` manda `"type": "capability"`, y la app parsea
  literalmente `"capability"`. Coinciden; una `s` de diferencia habría apagado el
  aviso de "sin voz" en silencio.
- `turn` lo pone la app y vuelve sin tocar en `segment`, `done` y `error`.
- `done` sale siempre, también sin segmentos, porque el `final` vacío del STT es una
  respuesta y no un error.

La tabla completa, lado por lado, quedó en
`../signall-android/reestructuracion/03-contrato.md`.

## Pendiente

- Los nombres internos de este repositorio (documentación, log de arranque, compose)
  siguen diciendo `SignAI`; eso pertenece al bloque de nombres del backend, no al
  contrato, y no se tocó acá.
