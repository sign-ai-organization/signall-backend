# Fase 5 del plan de implementación 2 — caché recargable e interfaz del orquestador

- **Fecha:** 2026-11-06
- **Rama:** `fix/fases1-3`
- **Base:** el merge de la Fase 2 (`1ecc2e9`) y la Fase 4 de Android ya en su rama.
- **Qué faltaba:** en ninguna rama de ningún repo estaba la Fase 5. Se implementó acá.

## 1. `POST /admin/cache/reload` (CAC-05)

**El problema:** `SemanticCache.load_all()` corre una sola vez, al arrancar. Un `UPDATE` o
un `DELETE` hechos a mano en Neon no se veían hasta reiniciar el contenedor, y reiniciar
tira todas las sesiones WebSocket abiertas: la app se reconecta, el avatar se queda a
medias y hay que volver a escribir la frase para saber si el cambio sirvió.

**Lo que se agregó:**

| Archivo | Qué |
|---|---|
| `app/nlp/semantic_cache.py` | `reload()`: lee las filas, arma el índice aparte y lo cambia de una sola vez |
| `app/controller/admin.py` | `POST /admin/cache/reload`, protegido con `X-Admin-Token` |
| `app/config/settings.py` | `ADMIN_TOKEN`, vacío por defecto |
| `app/main.py` | se incluye el router de administración |

**Por qué un endpoint y no `LISTEN/NOTIFY`:** el plan ofrece las dos y elige la simple
para el caso medido —una edición manual de vez en cuando, no una tabla que cambia sola—.
`LISTEN/NOTIFY` agrega una conexión dedicada y un camino que nadie mira hasta que falla.

**Por qué un token:** el backend no está detrás de un proxy que autentique y en una
demostración es alcanzable desde la red local. La ruta no borra nada, pero es una palanca:
cualquiera que llegue al puerto puede hacer que el servicio golpee la base en un bucle.
Con `ADMIN_TOKEN` vacío la ruta responde 404, como si no existiera; con un token
equivocado, 403; el token va en la cabecera y no en la URL, porque la URL termina en los
logs y en el historial del shell.

**La regla que hace que una recarga fallida no sea un paso atrás:** las filas se leen
**antes** de tocar el índice. Si la lectura falla, el índice viejo sigue sirviendo y el
endpoint responde 503 diciendo que se sigue usando el anterior — `reload()` no atrapa la
excepción, la propaga, y el endpoint la convierte en estado HTTP. El cambio de índice es
una sola asignación, así que ninguna consulta ve un índice a medio armar.

**Lo que NO recarga:** el catálogo. `catalog` y `catalog_synonym` también se leen una sola
vez, y la copia contra la que repara el modelo vive dentro de `LLMClient`; refrescarla es
otro cambio. Después de un seed, el contenedor se sigue reiniciando. Queda dicho en el
docstring del endpoint y en `.env.example`.

## 2. `OrchestratorService` (TRA-01)

`NLPService` y `ValidatorService` ya eran clases abstractas; `Orchestrator` —el que las
pega— no, y por eso `controller.py` importaba la clase concreta. Se extrajo
`app/orchestrator/orchestrator_service.py` con `translate` y `translate_stream`, y
`Orchestrator` ahora hereda de ahí. `Controller` recibe `OrchestratorService`.

Detalle que se ve al escribirlo: `translate_stream` se declara con `def`, no con
`async def`, porque la implementación es un generador asíncrono: lo que devuelve es el
iterador, no una corrutina que lo produce.

## Verificación

`ruff` limpio y `mypy` sin errores (42 archivos).

Scripts nuevos, los dos sin base ni modelo:

- `scripts/verify_cache_reload.py`: una fila editada y una borrada por SQL se ven después
  de `reload()`; una insertada también; una lectura que falla deja la caché anterior
  sirviendo; con `SEMANTIC_CACHE_PRELOAD=false` la recarga devuelve 0 y no marca la caché
  como cargada.
- `scripts/verify_orchestrator_interface.py`: la base abstracta no se puede instanciar, una
  subclase sin `translate_stream` tampoco, `Orchestrator` es un `OrchestratorService` y
  `translate`/`translate_stream` siguen devolviendo lo mismo.

`scripts/verify_endpoints.py` ganó el guardián de la ruta: 404 sin `ADMIN_TOKEN`, 403 sin
cabecera o con token equivocado (sin tocar la caché), 200 con el correcto y 503 cuando la
lectura falla.

Dos scripts viejos que fallaban por motivos ajenos quedaron arreglados de paso:
`verify_cache_upsert` (su doble de pool no aceptaba el `timeout` que la caché ya le pasaba)
y `verify_semantic_cache` (importaba `create_pool`, que ya no existe; ahora usa `open_pool`).

**Suite completa contra el contenedor:** los únicos que fallan son los cuatro que ya
fallaban en `main` —`verify_audio_validation` (7), `verify_client_frames` (14),
`verify_done_on_error` (9), `verify_turn_id` (2)—, por dobles de prueba viejos frente a los
frames `capability` y `turn_id`. El cambio no suma ninguno.

## Prueba en vivo (Neon + contenedor reconstruido)

Con `ADMIN_TOKEN` puesto en `.env` (que está gitignoreado):

```
POST sin cabecera                 -> 403
POST con token equivocado         -> 403
POST con token correcto           -> {"status":"ok","rows":44,"cache_rows":44}
```

La prueba que importa no es el contador sino que la recarga cambie lo que responde el
pipeline. Se insertó una fila por SQL **después** de que el backend arrancara, imitando la
edición manual:

```sql
INSERT INTO semantic_cache (original_text, embedding, phrase_type, glosses, ...)
SELECT 'frase de prueba de recarga', embedding, 'AFFIRMATIVE', ARRAY['PRUEBA'], ...
FROM semantic_cache LIMIT 1;
```

`POST /admin/cache/reload` devolvió `rows: 45` y la frase se mandó por el WebSocket:

```
segmento: [{'text': 'PRUEBA', 'available': False, ...}]
rt_cache_total{source="exact"} 1
```

Salió `PRUEBA` desde `exact`, sin llamar al LLM: la fila que no existía cuando el proceso
arrancó se está sirviendo. Después se borró la fila, se recargó y el contador volvió a 44.

## Estado

- Commit en `fix/fases1-3`, subido a `origin/fix/fases1-3`.
- Backend reconstruido y arriba con 63 glosas y 44 filas de caché.
- `ADMIN_TOKEN` está en el `.env` local (no versionado); `.env.example` lo documenta vacío.
