"""Verifica los frames de texto que el cliente Android envia al backend.

El backend acepta audio binario, pero el cliente Android ademas manda dos frames
de texto que antes se descartaban en silencio:

- ``{"type": "text", "text": "<frase>"}`` -- una frase escrita en vez de hablada.
- ``{"type": "end"}`` -- el usuario solto el microfono, asi que el silencio que
  cierra un segmento del STT nunca va a llegar y hay que cerrarlo a la fuerza.

Este script no necesita Neon, ni el LLM, ni el servicio STT: el cliente del STT
y el orquestador se reemplazan por dobles de prueba. Corre con

    python -m scripts.verify_client_frames
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Settings exige estos campos aunque el script no toque la base de datos.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")

# Este script verifica el protocolo de frames, no las trazas de debug. Se
# fuerza el apagado (y no un setdefault) porque un .env local con
# DEBUG_TRACE_ENABLED=true encendia las sentence_trace, que este test no
# ejercita: send_segment indexa trace.sentences y el orquestador falso de abajo
# no llena esa lista, porque no pasa por trace_sentence.
os.environ["DEBUG_TRACE_ENABLED"] = "false"

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config.settings import settings  # noqa: E402
from app.controller import router as router_module  # noqa: E402
from app.controller.router import END_FRAME, TEXT_FRAME, _parse_client_frame  # noqa: E402
from app.domain.models import Gloss, PhraseType, ValidatedSegment  # noqa: E402
from app.realtime.incremental import IncrementalTranslator, TranscriptUpdate  # noqa: E402

failures: list[str] = []

TYPED_PHRASE = '{"type":"text","text":"hola, como estas"}'
# Una frase escrita de dos oraciones produce transcript, un segment por
# oraciones y done.
FOUR_MESSAGES = ["transcript", "segment", "segment", "done"]


def check(name: str, got, expected) -> None:
    ok = got == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        esperado: {expected!r}")
        print(f"        obtenido: {got!r}")
        failures.append(name)


# -- El clasificador de frames ------------------------------------------------

print("\n_parse_client_frame")
check("frase escrita", _parse_client_frame(TYPED_PHRASE), (TEXT_FRAME, "hola, como estas"))
check("recorta los espacios", _parse_client_frame('{"type":"text","text":"  hola  "}'), (TEXT_FRAME, "hola"))
check("cierre de microfono", _parse_client_frame('{"type":"end"}'), (END_FRAME, ""))
check("ignora frase vacia", _parse_client_frame('{"type":"text","text":"   "}'), None)
check("ignora tipo desconocido", _parse_client_frame('{"type":"nope"}'), None)
check("ignora JSON invalido", _parse_client_frame("no soy json"), None)
check("ignora un array", _parse_client_frame("[1,2]"), None)
check("ignora texto que no es string", _parse_client_frame('{"type":"text","text":42}'), None)
check("ignora frame sin type", _parse_client_frame('{"text":"hola"}'), None)


# -- La sesion completa -------------------------------------------------------


class FakeSttClient:
    """Doble del cliente del STT: guarda lo que se le mando, sin red.

    Los contadores son de clase a proposito: el router construye el cliente
    interno, asi que la prueba no tiene una referencia directa a la instancia.
    """

    sent_audio: list[bytes] = []
    end_calls = 0
    # Si se llena, `receive_transcript` devuelve estos mensajes en orden y
    # despues cierra el ciclo. Es lo que permite ejercitar el modo en tiempo
    # real sin un Whisper de verdad.
    scripted: list[TranscriptUpdate] = []

    def __init__(self, url: str) -> None:
        self.url = url

    async def connect(self) -> None:
        return None

    async def send_audio(self, chunk: bytes) -> None:
        FakeSttClient.sent_audio.append(chunk)

    async def send_end(self) -> None:
        FakeSttClient.end_calls += 1

    async def receive_transcript(self) -> TranscriptUpdate | None:
        # None cierra el ciclo de transcripcion. El otro lado del gather
        # (_forward_audio) sigue leyendo, asi que la sesion queda abierta
        # hasta que el cliente la cierra, que es el comportamiento real.
        if FakeSttClient.scripted:
            return FakeSttClient.scripted.pop(0)
        return None

    async def close(self) -> None:
        return None


class FakeKeepAlive:
    def wake_up(self) -> None:
        return None

    def mark_activity(self) -> None:
        return None


def fake_segment() -> ValidatedSegment:
    return ValidatedSegment(
        type=PhraseType.AFFIRMATIVE,
        glosses=[Gloss(text="HOLA", available=True, glb_path="/static/hola.glb")],
    )


class FakeOrchestrator:
    async def translate_stream(self, text: str):
        yield 0, 2, fake_segment()
        yield 1, 2, fake_segment()

    def incremental_translator(self, **kwargs) -> IncrementalTranslator:
        # El translator real, con un atajo de traducción que no necesita base
        # ni LLM. Lo que se prueba aca es el protocolo, no la traducción.
        return IncrementalTranslator(self.translate_fragment, **kwargs)

    async def translate_fragment(self, text: str) -> ValidatedSegment:
        return ValidatedSegment(
            type=PhraseType.AFFIRMATIVE,
            glosses=[Gloss(text=word.upper(), available=True) for word in text.split()],
        )


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    app.state.db_keep_alive = FakeKeepAlive()
    app.state.orchestrator = FakeOrchestrator()
    return app


def _update(text: str, final: bool = False) -> TranscriptUpdate:
    """Una actualización del STT con timestamps de 300 ms por palabra.

    Los `end_ms` quedan en `(i+1) * 300 - 100` y el audio capturado termina
    justo donde termina la última palabra (`len * 300`), que es lo que pasa
    mientras la persona sigue hablando sin pausar. Con el margen de 180 ms de
    `settings`, eso deja siempre una palabra sin firmar: la que se está
    formando. Es el caso normal de producción.
    """
    tokens = text.split()
    words = tuple(
        (word, index * 300.0, (index + 1) * 300.0 - 100.0)
        for index, word in enumerate(tokens)
    )
    return TranscriptUpdate(text=text, final=final, words=words, audio_ms=len(tokens) * 300.0)


def read_exactly(websocket, count: int) -> list[dict]:
    """Lee un numero exacto de mensajes.

    La sesion vive hasta que el cliente la cierra, asi que no se puede leer
    "hasta que termine": hay que saber cuantos van a llegar. Para una frase
    escrita son cuatro, y esa misma respuesta sirve como senal de avance: cuando
    llega, los frames anteriores --audio y `end`-- ya se procesaron, porque
    viajan por el mismo socket en orden.
    """
    return [websocket.receive_json() for _ in range(count)]


def main() -> None:
    # El router construye el cliente del STT con este nombre; sustituirlo ahi
    # alcanza para que la sesion no intente conectarse a un servicio real.
    router_module.SttServiceClientImpl = FakeSttClient  # type: ignore[assignment]

    # Los dos modos responden con un numero distinto de mensajes, asi que cada
    # bloque dice explicitamente en cual corre. El camino viejo (frase completa
    # en un lote) y el de tiempo real (un fragmento por cola nueva) se prueban
    # por separado y asi una regresion en uno no se esconde en el otro.
    legacy_settings = settings.model_copy(update={"realtime_enabled": False})
    realtime_settings = settings.model_copy(update={"realtime_enabled": True})
    original_settings = router_module.settings

    try:
        router_module.settings = legacy_settings

        print("\nsesion: frase escrita")
        with TestClient(build_app()) as client:
            with client.websocket_connect("/ws/translate") as ws:
                ws.send_text(TYPED_PHRASE)
                messages = read_exactly(ws, 4)
        check("responde transcript, 2 segment y done", [m.get("type") for m in messages], FOUR_MESSAGES)
        check("la frase es la que se mando", messages[0].get("text"), "hola, como estas")
        check("el primer segment es 0 de 2", [messages[1].get("index"), messages[1].get("total")], [0, 2])
        check("el segundo segment es 1 de 2", [messages[2].get("index"), messages[2].get("total")], [1, 2])
        check("no se mandaron frames de end", FakeSttClient.end_calls, 0)

        print("\nsesion: audio y cierre de microfono")
        FakeSttClient.sent_audio.clear()
        FakeSttClient.end_calls = 0
        with TestClient(build_app()) as client:
            with client.websocket_connect("/ws/translate") as ws:
                ws.send_bytes(b"\x01\x02" * 480)
                ws.send_bytes(b"\x03\x04" * 480)
                ws.send_text('{"type":"end"}')
                # La frase escrita va al final a proposito: cuando responde, los
                # frames anteriores ya pasaron por el socket.
                ws.send_text(TYPED_PHRASE)
                messages = read_exactly(ws, 4)
        check(
            "el audio llega crudo al STT",
            FakeSttClient.sent_audio,
            [b"\x01\x02" * 480, b"\x03\x04" * 480],
        )
        check("'end' se reenvia al STT", FakeSttClient.end_calls, 1)
        check("y la sesion sigue traduciendo", [m.get("type") for m in messages], FOUR_MESSAGES)

        print("\nsesion: frame desconocido no tumba la sesion")
        with TestClient(build_app()) as client:
            with client.websocket_connect("/ws/translate") as ws:
                ws.send_text("basura que no es json")
                ws.send_text('{"type":"desconocido"}')
                ws.send_text('{"type":"text","text":"   "}')
                ws.send_text(TYPED_PHRASE)
                messages = read_exactly(ws, 4)
        check("la sesion sigue viva", [m.get("type") for m in messages], FOUR_MESSAGES)

        print("\nsesion: tiempo real")
        router_module.settings = realtime_settings

        print("\nsesion: frase escrita en tiempo real")
        with TestClient(build_app()) as client:
            with client.websocket_connect("/ws/translate") as ws:
                ws.send_text(TYPED_PHRASE)
                # Una sola pasada: en tiempo real la frase entera es un
                # fragmento, no uno por oración.
                messages = read_exactly(ws, 3)
        check("responde transcript, segment y done", [m.get("type") for m in messages], [
            "transcript", "segment", "done",
        ])
        check("lleva stream=true", messages[1].get("stream"), True)
        check("y no es provisional (una frase escrita ya es final)", messages[1].get("provisional"), False)

        # -- El modo en tiempo real con hipótesis crecientes --------------------

        FakeSttClient.scripted = [
            # Tres hipótesis crecientes. Cada una deja la anterior "firmada" salvo
            # la última palabra, que es la que todavía se está formando.
            _update("hola"),
            _update("hola como"),
            _update("hola como estas", final=True),
        ]

        with TestClient(build_app()) as client:
            with client.websocket_connect("/ws/translate") as ws:
                messages = read_exactly(ws, 6)

        FakeSttClient.scripted = []

        kinds = [m.get("type") for m in messages]
        check(
            "cada hipótesis produce transcript, dos fragmentos y un done",
            kinds,
            ["transcript", "transcript", "transcript", "segment", "segment", "done"],
        )
        check("los índices de fragmento son correlativos", [m.get("index") for m in messages[3:5]], [0, 1])
        check("total es 0 porque en un utterance abierto no se sabe", [m.get("total") for m in messages[3:5]], [0, 0])
        check("los fragmentos vienen marcados como stream", [m.get("stream") for m in messages[3:5]], [True, True])
        check(
            "el último fragmento es el definitivo",
            [m.get("provisional") for m in messages[3:5]],
            [True, False],
        )
        check(
            "cada fragmento lleva el texto del que salió",
            [m.get("source_text") for m in messages[3:5]],
            ["hola", "como estas"],
        )
        check(
            "un cliente viejo ve un segment con la forma de siempre",
            sorted(messages[3].keys()),
            sorted(["type", "index", "total", "segment", "stream", "provisional", "source_text"]),
        )
    finally:
        router_module.settings = original_settings

    print()
    if failures:
        print(f"FALLARON {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("todo OK")


if __name__ == "__main__":
    main()