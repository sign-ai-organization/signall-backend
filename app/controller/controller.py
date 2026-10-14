"""Traducción por sesión: el WebSocket del cliente Android y el del STT.

Dos modos, mismo código de salida:

- **Por frase** (el de antes): se espera el `final` del STT y se manda la
  traducción completa en un lote.
- **Tiempo real**: cada actualización del STT que trae palabras ya terminadas
  produce un fragmento que se manda en el acto, sin esperar al final.

El punto donde estaba la latencia
---------------------------------

La versión anterior hacía esto, dentro del bucle que lee del STT:

    text, is_final = await stt_client.receive_transcript()
    await self.handle_transcript(text, is_final)   # <- traduce aquí adentro

Mientras la traducción corría, **no se leía el siguiente mensaje del STT**. Con
el LLM en medio, eso significa que un `final` podía quedar atrás en el socket
mientras el avatar seguía esperando por él. Ahora la traducción va en una tarea
aparte y el bucle de lectura sigue drenando el STT.
"""

import asyncio
import audioop
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import WebSocket

from app.config.settings import Settings
from app.controller.stt_service_client import SttServiceClient
from app.domain.models import ValidatedSegment
from app.metrics import metrics, metrics_timer
from app.observability.pipeline_trace import PipelineTrace, start_trace, trace_step
from app.orchestrator.orchestrator import Orchestrator
from app.realtime.incremental import IncrementalTranslator, TranscriptUpdate, TranslationChunk

logger = logging.getLogger(__name__)

# Modos de captura que pide el cliente con `{"type":"mode","mode":...}`.
#
# `realtime` es el comportamiento de siempre: cada fragmento del STT se traduce
# y se manda en el acto, así que el muñeco firma mientras la persona habla.
# `dictation` es solo transcripción: el texto vuelve al input y el usuario
# decide cuándo mandarlo a traducir con el botón Traducir.
CAPTURE_REALTIME = "realtime"
CAPTURE_DICTATION = "dictation"
CAPTURE_MODES = (CAPTURE_REALTIME, CAPTURE_DICTATION)


class Controller:
    def __init__(
        self,
        websocket: WebSocket,
        orchestrator: Orchestrator,
        stt_client: SttServiceClient,
        settings: Settings,
        debug_trace_enabled: bool = False,
    ) -> None:
        self.websocket = websocket
        self.orchestrator = orchestrator
        self.stt_client = stt_client
        self.settings = settings
        self.debug_trace_enabled = debug_trace_enabled

        self._realtime: IncrementalTranslator | None = None
        if settings.realtime_enabled:
            self._realtime = orchestrator.incremental_translator(
                settle_margin_ms=settings.realtime_settle_margin_ms,
                batch_words=settings.realtime_batch_words,
                max_segments=settings.realtime_max_segments,
            )

        # Traducciones en vuelo. El bucle de lectura del STT las encola y sigue:
        # si esperara adentro, un final se atrasaría detrás de un LLM en curso.
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._on_final: list[Callable[[], Awaitable[None]]] = []

        # Modo de captura pedido por el cliente. Es el interruptor que decide si
        # lo que entra por el micrófono además se traduce: en `dictation` el
        # texto vuelve al input y nada más, y en `realtime` cada fragmento se
        # firma mientras se habla.
        self._capture_mode = CAPTURE_REALTIME

        # Modo con el que **empezó** el utterance en curso.
        #
        # El cliente manda `end` y después cambia de modo, así que el `final` del
        # utterance viejo llega cuando el modo de la sesión ya es el nuevo. Sin
        # este cierre el backend cerraría el dictado como tiempo real (y firmaría
        # lo que el usuario solo quería escribir) o, al revés, dejaría la última
        # frase de TR sin firmar. Se fija con la primera transcripción y dura
        # hasta el `final`: un utterance es de un solo modo, de punta a punta.
        self._utterance_mode: str | None = None

        # Contexto de utterance para las métricas: cuándo empezó a hablar la
        # persona y cuándo se emitió la primera seña. Es el número que hay que
        # mirar para saber si el producto se siente en tiempo real. Todo esto es
        # por sesión: dos clientes hablando a la vez no se pisan.
        self._utterance_started_at: float | None = None
        self._first_segment_at: float | None = None
        self._segments_sent = 0

        # Audio reenviado al STT en esta sesión. Es el único tramo del sistema
        # que no produce salida visible, así que necesita su propio contador.
        self._audio_bytes = 0
        self._audio_chunks = 0
        self._audio_rms_total = 0.0

    # ---------------------------------------------------------------- audio

    async def handle_audio_chunk(self, chunk: bytes) -> None:
        """Reenvía un fragmento de audio al STT y mide que realmente esté fluyendo.

        El audio es el único tramo del sistema que no produce salida: si el
        micrófono del teléfono se rompe, el STT se queda mudo y no hay ningún
        `segment` que llegue. Lo único que se ve es este contador, y por eso
        cuenta bytes además de fragmentos: distingue "el teléfono no manda
        nada" de "manda el doble de lo que debería".

        El nivel importa tanto como el volumen. Bytes que llegan pero son
        silencio tienen exactamente el mismo síntoma que un STT roto —la
        transcripción nunca aparece— y `audio_rms` es lo que separa los dos.
        En la práctica un nivel bajo tiene tres causas distintas que se
        distinguen mirando `audio_rms` junto con `audio_bytes_total`:

        - micrófono tapado o permissions mal resueltas;
        - volumen del sistema en cero;
        - el `AudioSource.VOICE_RECOGNITION` del Android cancelando el eco del
          altavoz, que es justo lo que hace bien y lo que impide probar el
          micrófono con el audio del propio teléfono.
        """
        await self.stt_client.send_audio(chunk)
        self._audio_bytes += len(chunk)
        self._audio_chunks += 1
        metrics.counter("audio_bytes_total", len(chunk))
        metrics.counter("audio_chunks_total")
        metrics.gauge("session_audio_bytes", self._audio_bytes)

        rms = _pcm16_rms(chunk)
        # Media móvil: un chunk es 30 ms y llegaran muchos por segundo, así que
        # la media entera mide el nivel sostenido, que es lo que interesa.
        self._audio_rms_total += rms
        metrics.gauge("session_audio_rms", self._audio_rms_total / self._audio_chunks)
        metrics.histogram("audio_rms", rms, "Nivel RMS por fragmento de audio entrante")

    def audio_stats(self) -> tuple[int, int]:
        """(bytes, rms promedio) capturados en esta sesión. Para tests y diagnóstico."""
        return self._audio_bytes, self._audio_rms_total / max(1, self._audio_chunks)

    async def handle_text(self, text: str) -> None:
        """Translate a phrase the client typed instead of spoke.

        A typed phrase is already final by construction, so it takes the
        non-realtime path: there is no growing hypothesis to follow, and holding
        a typed sentence back for a silence timeout would be absurd.

        El modo de captura manda sobre la voz, no sobre el texto. Si el usuario
        dictó algo, apagó el micrófono y apretó Traducir, el último `mode` que
        bajó fue `dictation`; si esta función lo respetara, la frase escrita
        nunca se traduciría. Escribir una frase **es** la orden de traducirla,
        así que este camino no consulta el modo.
        """
        update = TranscriptUpdate(text=text, final=True)
        await self.send_transcript(update.text, update.final)
        await self._translate(update)

    def set_mode(self, mode: str) -> None:
        """Cambia cómo se trata lo que llega por el micrófono.

        Llega como `{"type":"mode","mode":"dictation"|"realtime"}`. Es estado de
        la sesión, no del utterance: el modo del utterance en curso ya está
        fijado en `_utterance_mode` y no se toca acá.
        """
        if mode not in CAPTURE_MODES:
            logger.warning("ignoring unknown capture mode %r", mode)
            return
        if mode == self._capture_mode:
            return

        if self._utterance_mode is not None:
            # No es un error: el cliente manda `end` y después cambia de modo, y
            # el `final` de ese utterance llega después del cambio. Se cuenta
            # igual, porque si este número crece es que hay un cliente que
            # cambia de modo a mitad de una frase y de eso hay que enterarse.
            metrics.counter("capture_mode_switch_open_utterance_total")
            logger.info(
                "capture mode %s -> %s con un utterance abierto: se cierra como %s",
                self._capture_mode,
                mode,
                self._utterance_mode,
            )

        self._capture_mode = mode
        metrics.counter(f"capture_mode_{mode}_total")
        metrics.gauge(
            "session_capture_dictation",
            1.0 if mode == CAPTURE_DICTATION else 0.0,
        )
        logger.info("capture mode -> %s", mode)

    async def handle_end(self) -> None:
        """Close the utterance the STT has open.

        The STT ends a segment when it hears silence. A client that stops
        capturing — the Android mic toggle — never sends that silence, so the
        segment would stay open and no final transcript would ever arrive.
        The STT protocol has a frame for exactly this case.

        Failures are logged, not raised: this runs on the session's read path,
        and letting it throw would take down a session that is otherwise fine.
        """
        try:
            await self.stt_client.send_end()
        except Exception:
            logger.exception("could not forward end-of-utterance to the STT service")

    def on_final_sent(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Registra un callback que corre cuando terminó el utterance en curso.

        Lo usa el router para marcar actividad en la base de datos, que es una
        operación lenta y no puede quedar en la línea de tiempo del cliente.
        """
        self._on_final.append(callback)

    # --------------------------------------------------------- transcripciones

    async def handle_transcript(self, update: TranscriptUpdate) -> None:
        """Recibe una actualización del STT y decide qué hacer con ella.

        Se pasa el `TranscriptUpdate` entero y no solo el texto porque los
        `words` son lo que permite distinguir "la persona ya terminó de decir
        esta palabra" de "todavía la está formando". Si se descartaran aquí, el
        modo en tiempo real degrada a la heurística gruesa sin avisar.

        Este camino es el de la **voz**: el modo de captura decide si además de
        transcribir se traduce. El texto escrito va por [handle_text].
        """
        if self._utterance_mode is None:
            self._utterance_mode = self._capture_mode
        dictation = self._utterance_mode == CAPTURE_DICTATION

        # El flag viaja en la transcripción y no se deduce del estado del
        # cliente porque el cliente ya lo cambió: el `end` que manda al apagar el
        # dictado llega **después** del interruptor, así que el `final` de lo
        # dictado vuelve cuando la app ya se cree con el micrófono apagado. Sin
        # esto tomaría esa frase por una de tiempo real, esperaría fragments que
        # no van a llegar y quedaría en "Traduciendo..." para siempre.
        await self.send_transcript(update.text, update.final, dictation=dictation)

        if not update.text.strip():
            return

        if dictation:
            # Dictado: la transcripción ya salió arriba y con eso alcanza. No se
            # toca el LLM ni se manda un `segment`, así que el muñeco no se
            # mueve: lo que el usuario dictó es texto, hasta que apretó Traducir.
            #
            # Un `final` del STT no significa "terminó el dictado" —el STT los
            # cierra por silencio, y alguien que dicta hace pausas—, así que acá
            # solo se libera el utterance para el siguiente.
            if update.final:
                metrics.counter("dictation_utterances_total")
                metrics.histogram(
                    "dictation_utterance_words",
                    len(update.text.split()),
                    "Palabras por frase dictada",
                )
                self._utterance_mode = None
                logger.info("dictated: %r", update.text)
            return

        await self._translate(update)

    async def _translate(self, update: TranscriptUpdate) -> None:
        """Traduce una transcripción: por fragmentos en tiempo real, o de una."""
        if self._realtime is not None:
            self._start_utterance()
            # Traducir fuera del bucle de lectura es lo que permite que el STT
            # siga hablando mientras el LLM piensa.
            await self._queue.put(update)
            if update.final:
                await self._drain()
            return

        await self._translate_whole_phrase(update)

    def _start_utterance(self) -> None:
        if self._utterance_started_at is None:
            self._utterance_started_at = time.monotonic()
            self._first_segment_at = None
            metrics.counter("stt_utterances_total")

    async def _drain(self) -> None:
        """Espera a que se vacíe la cola de traducciones.

        Solo se llama en el `final`: es el punto donde el backend ya no puede
        recibir más texto de esta frase y el `done` debe ir después del último
        fragmento.
        """
        await self._queue.join()

    async def _translate_whole_phrase(self, update: TranscriptUpdate) -> None:
        """El camino de frase completa: espera el final y manda todo junto."""
        if not update.final:
            return

        # A partir de acá el utterance está completo: el siguiente vuelve a
        # tomar el modo que la sesión tenga ahora.
        self._utterance_mode = None

        logger.info("Final transcript: %r -> translating", update.text)
        with start_trace() as trace:
            try:
                with trace_step("total"):
                    async for index, total, segment in self.orchestrator.translate_stream(update.text):
                        await self.send_segment(index, total, segment, trace)
            except Exception:
                logger.exception("orchestrator.translate_stream failed for %r", update.text)
                logger.info("Pipeline trace for %r: %s", update.text, trace.to_dict())
                await self.send_error("No se pudo traducir el texto.")
                return

        logger.info("Pipeline trace for %r: %s", update.text, trace.to_dict())
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "trace", "steps_ms": trace.to_dict()["steps_ms"]})
        await self.websocket.send_json({"type": "done"})

    # ------------------------------------------------------------- tiempo real

    def start_realtime_worker(self) -> None:
        if self._realtime is None or self._worker is not None:
            return
        self._worker = asyncio.create_task(self._drain_loop(), name="translate-worker")

    async def _drain_loop(self) -> None:
        """Traduce en segundo plano mientras el bucle de lectura sigue libre."""
        while True:
            update: TranscriptUpdate = await self._queue.get()
            if update is None:  # pragma: no cover - centinela de cierre
                self._queue.task_done()
                return

            try:
                with start_trace() as trace:
                    await self._handle_realtime_update(update, trace)
            except Exception:
                logger.exception("realtime translation failed for %r", update.text)
                await self.try_send_error("No se pudo traducir el texto.")
            finally:
                self._queue.task_done()

    async def _handle_realtime_update(self, update: TranscriptUpdate, trace: PipelineTrace) -> None:
        assert self._realtime is not None

        with trace_step("total"):
            with metrics_timer(
                "rt_update_ms", "De una actualización del STT a los fragmentos enviados"
            ) as timer:
                chunks = await self._realtime.update(update)

        for chunk in chunks:
            if not self._realtime.should_emit(chunk.index):
                logger.warning("fragment %d suppressed by the per-utterance cap", chunk.index)
                continue
            await self.send_realtime_chunk(chunk, trace)

        if update.final:
            await self._finish_utterance(update.text, timer.elapsed_ms)

    async def _finish_utterance(self, final_text: str, last_update_ms: float) -> None:
        assert self._realtime is not None
        self._realtime.reset()
        self._utterance_mode = None

        logger.info("Final transcript: %r", final_text)
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "trace", "steps_ms": {}})
        await self.websocket.send_json({"type": "done"})

        for callback in self._on_final:
            try:
                await callback()
            except Exception:
                logger.exception("post-final callback failed")

        self._record_utterance_timings(final_text, last_update_ms)

    def _record_utterance_timings(self, final_text: str, last_update_ms: float) -> None:
        """Cierra las métricas del utterance y las publica.

        `rt_utterance_ms` es la latencia de extremo a extremo que percibe el
        usuario: desde que llegó el primer fragmento de texto hasta que se envió
        la última seña. Es el número que define si esto es tiempo real o una
        demostración rápida.
        """
        if self._utterance_started_at is None:
            return

        total_ms = (time.monotonic() - self._utterance_started_at) * 1000
        first_ms = (
            (self._first_segment_at - self._utterance_started_at) * 1000
            if self._first_segment_at is not None
            else -1.0
        )

        metrics.counter("rt_utterances_total")
        metrics.counter("rt_glosses_total", self._segments_sent)
        metrics.histogram("rt_utterance_ms", total_ms, "Ultima seña enviada menos primer texto recibido")
        metrics.histogram("rt_first_sign_ms", first_ms, "Primera seña enviada menos primer texto recibido")
        metrics.histogram("rt_last_update_ms", last_update_ms, "Ultimo fragmento del STT a su traduccion")
        metrics.gauge("rt_utterance_segments", self._segments_sent)
        metrics.gauge("rt_utterance_in_progress", 0)

        logger.info(
            "utterance done: texto=%r fragmentos=%d primera_seña=%.0fms total=%.0fms",
            final_text,
            self._segments_sent,
            first_ms,
            total_ms,
        )

        self._utterance_started_at = None
        self._first_segment_at = None
        self._segments_sent = 0

    # ---------------------------------------------------------------- salida

    async def send_transcript(
        self,
        text: str,
        is_final: bool,
        dictation: bool = False,
    ) -> None:
        """Manda una transcripción.

        `dictation` le dice al cliente de qué modo salió. Es aditivo: un cliente
        que no lo conoce sigue leyendo `type`, `text` y `final` igual que antes.
        """
        await self.websocket.send_json(
            {
                "type": "transcript",
                "text": text,
                "final": is_final,
                "dictation": dictation,
            }
        )

    async def send_segment(self, index: int, total: int, segment: ValidatedSegment, trace: PipelineTrace) -> None:
        logger.info("Sending segment %d/%d: %s", index + 1, total, segment)
        if self.debug_trace_enabled:
            await self.websocket.send_json({"type": "sentence_trace", "index": index, **trace.sentence_dict(index)})
        await self.websocket.send_json(
            {"type": "segment", "index": index, "total": total, "segment": segment.model_dump(mode="json")}
        )

    async def send_realtime_chunk(self, chunk: TranslationChunk, trace: PipelineTrace) -> None:
        """Manda un fragmento en el acto.

        `stream: true` es lo que le dice al cliente que lo fiddle ahora y no
        espere a un `total` que en un utterance abierto no existe. `total: 0` es
        la señal explícita de "todavía no se sabe cuántas son", para que un
        cliente que no conoce `stream` no se quede esperando un final imposible.

        El campo nuevo es aditivo: un cliente que ignore lo que no conoce sigue
        recibiendo `segment` con la misma forma de siempre.
        """
        if self._first_segment_at is None:
            self._first_segment_at = time.monotonic()
            metrics.gauge("rt_utterance_in_progress", 1)
        self._segments_sent += 1

        elapsed_ms = (
            (self._first_segment_at - self._utterance_started_at) * 1000
            if self._utterance_started_at is not None
            else 0.0
        )
        metrics.counter("rt_chunks_total", labels={"provisional": "1" if chunk.provisional else "0"})
        metrics.histogram("rt_chunk_delay_ms", elapsed_ms, "Fragmento enviado menos primer texto recibido")

        logger.info(
            "Sending realtime fragment %d: %s (%s)",
            chunk.index,
            [gloss.text for gloss in chunk.segment.glosses],
            "provisional" if chunk.provisional else "final",
        )
        if self.debug_trace_enabled:
            await self.websocket.send_json(
                {
                    "type": "sentence_trace",
                    "index": chunk.index,
                    "text": chunk.source_text,
                    "source": "realtime",
                    "steps_ms": {},
                }
            )
        await self.websocket.send_json(
            {
                "type": "segment",
                "index": chunk.index,
                "total": 0,
                "stream": True,
                "provisional": chunk.provisional,
                "source_text": chunk.source_text,
                "segment": chunk.segment.model_dump(mode="json"),
            }
        )

    async def send_error(self, message: str) -> None:
        logger.info("Sending error: %s", message)
        await self.websocket.send_json({"type": "error", "message": message})

    async def try_send_error(self, message: str) -> None:
        """Envía un error sin tumbar la sesión si el propio envío falla."""
        try:
            await self.send_error(message)
        except Exception:
            logger.exception("could not notify the client about the error")

    async def shutdown(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None


def _pcm16_rms(chunk: bytes) -> float:
    """RMS de un fragmento PCM16LE, en escala 0..1.

    Se calcula con `audioop` de la stdlib y no con numpy: es un `int` por
    muestra y corre en un fragmento de 480 muestras cada 30 ms por sesión, en
    el bucle de eventos. `audioop` es C puro y no suma una dependencia.

    Se recorta a un número par de bytes porque un chunk de red puede cortar una
    muestra por la mitad, y `audioop` lanza `ValueError` con eso.
    """
    usable = len(chunk) - (len(chunk) % 2)
    if usable <= 0:
        return 0.0
    try:
        return audioop.rms(chunk[:usable], 2) / 32768.0
    except ValueError:
        return 0.0