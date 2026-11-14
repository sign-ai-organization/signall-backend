# Los cuatro `verify_*` del contrato vuelven a pasar

- **Fecha:** 2026-11-14
- **Repo:** `signall-backend`
- **Qué pedía:** arreglar cuatro scripts de verificación que ya fallaban antes de esta sesión
  (`verify_audio_validation`, `verify_client_frames`, `verify_done_on_error`, `verify_turn_id`)
  para que la verificación del contrato vuelva a ser confiable.

## Resultado

| Script | Antes | Después |
|---|---|---|
| `verify_audio_validation` | 7 fallas | **0** |
| `verify_client_frames` | 14 fallas de 32 | **0** |
| `verify_done_on_error` | 9 fallas | **0** |
| `verify_turn_id` | 2 fallas | **0** |

Corridos dentro del contenedor contra el backend real, con la imagen reconstruida:

```
docker compose -f docker-compose.yml -f docker-compose.host.yml exec -T backend \
  python -m scripts.verify_client_frames      # idem los otros tres
```

Cinco vueltas seguidas de los cuatro con salida 0, para descartar que el paso fuera de suerte.

## La causa: dos cambios del contrato, no un bug

1. **`8a31cc2` — el frame `capability` abre la sesión.** El backend avisa si hay voz
   (`{"type":"capability","audio":true}`) antes de responder a cualquier frase, y el aviso se
   manda antes de crear las tareas de la sesión (`router.py:290`). Los scripts leían por
   posición, así que cada expectativa quedaba corrida un frame: esperaban
   `['transcript','transcript']` y recibían `['capability','transcript']`, y de ahí para
   adelante fallaba todo en cascada. Por eso `verify_turn_id` daba dos fallas que parecían de
   `turn` y no lo eran: `messages[0]` era el `capability`.
2. **`8631115` — la traducción corre en su propia tarea.** El eco de voz y los `segment` ya no
   tienen un orden fijo entre sí, así que donde el script dependía de una posición se sincroniza
   por contenido.

## Qué se cambió en los scripts

- Se **consume y comprueba** el `capability` de apertura en cada sesión (`expect_capability`,
  `open_session`). Comprobarlo en vez de saltarlo agrega una verificación del contrato en vez de
  quitarla.
- `verify_client_frames` lee la respuesta de una frase con `read_phrase`, que para en el `done`
  en lugar de contar frames. Lo que se compara después sigue siendo la lista exacta de frames
  (`['segment','segment','done']`): un frame de más hace fallar la comprobación.
- **No se aflojó ninguna exigencia**: siguen comparando listas exactas, mensajes de error,
  contadores de rechazo y `turn` en segment/done/error.

## Verificación

- `ruff check app scripts` en verde.
- `mypy` (la configuración del repo, `files = ["app"]`) en verde.
- `mypy app scripts` ya no reporta nada de los cuatro archivos tocados; sí quedan 27 errores en
  otros seis scripts, preexistentes y ajenos a este cambio.
- La imagen del servicio se reconstruyó (`docker compose ... build backend`) para que el comando
  `exec` documentado corra estos scripts y no la copia vieja horneada en la imagen anterior.

## Pendiente

- La entrada en `signall-docs/cambios/` no se escribió: esta sesión tenía la instrucción de no
  tocar otros repositorios.
- `verify_done_on_error` imprime el `traceback` del orquestador falso que falla a propósito; es
  ruido esperado del caso "la traducción falla", no una falla del script.
