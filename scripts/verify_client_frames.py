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

from app.controller import router as router_module  # noqa: E402
from app.controller.router import END_FRAME, TEXT_FRAME, _parse_client_frame  # noqa: E402
from app.domain.models import Gloss, PhraseType, ValidatedSegment  # noqa: E402

failures: list[str] = []

PHRASE_TEXT = "hola, como estas"
TYPED_PHRASE = '{"type":"text","text":"hola, como estas"}'
# Una frase escrita de dos oraciones produce transcript, un segment por
# oraciones y done.
# El eco de la frase escrita **no** se manda. Ver `Controller.handle_text`.
THREE_MESSAGES = ["segment", "segment", "done"]


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
    # Transcripciones que el doble emite al abrirse la sesion. Vacio = el ciclo
    # se cierra de una, como en las pruebas que no tienen STT.
    incoming: list[tuple[str, bool]] = []

    def __init__(self, url: str) -> None:
        self.url = url

    async def connect(self) -> None:
        return None

    async def send_audio(self, chunk: bytes) -> None:
        FakeSttClient.sent_audio.append(chunk)

    async def send_end(self) -> None:
        FakeSttClient.end_calls += 1

    async def receive_transcript(self):
        # None cierra el ciclo de transcripcion. El otro lado del gather
        # (_forward_audio) sigue leyendo, asi que la sesion queda abierta
        # hasta que el cliente la cierra, que es el comportamiento real.
        if not FakeSttClient.incoming:
            return None
        return FakeSttClient.incoming.pop(0)

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
    # Que frases llegaron a traducirse. Es el invariante central del flujo por
    # oraciones: solo lo que el cliente mando como `text` puede aparecer aca.
    calls: list[str] = []

    async def translate_stream(self, text: str):
        FakeOrchestrator.calls.append(text)
        yield 0, 2, fake_segment()
        yield 1, 2, fake_segment()


def build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    app.state.db_keep_alive = FakeKeepAlive()
    app.state.orchestrator = FakeOrchestrator()
    return app


def read_exactly(websocket, count: int) -> list[dict]:
    """Lee un numero exacto de mensajes.

    La sesion vive hasta que el cliente la cierra, asi que no se puede leer
    "hasta que termine": hay que saber cuantos van a llegar. Para una frase
    escrita son tres --una `segment` por oracion y un `done`--, y esa misma
    respuesta sirve como senal de avance: cuando llega, los frames anteriores
    --audio y `end`-- ya se procesaron, porque viajan por el mismo socket en
    orden.
    """
    return [websocket.receive_json() for _ in range(count)]


def main() -> None:
    # El router construye el cliente del STT con este nombre; sustituirlo ahi
    # alcanza para que la sesion no intente conectarse a un servicio real.
    router_module.SttServiceClientImpl = FakeSttClient  # type: ignore[assignment]

    print("\nsesion: frase escrita")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_text(TYPED_PHRASE)
            messages = read_exactly(ws, 3)
    check("responde 2 segment y done, sin eco", [m.get("type") for m in messages], THREE_MESSAGES)
    # Que no haya eco es la parte importante: un `transcript` con `final: true`
    # aqui seria indistinguible de la voz, y el cliente en vivo lo tomaria por
    # una frase nueva del microfono y la volveria a mandar.
    check("el primer segment es 0 de 2", [messages[0].get("index"), messages[0].get("total")], [0, 2])
    check("el segundo segment es 1 de 2", [messages[1].get("index"), messages[1].get("total")], [1, 2])
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
            messages = read_exactly(ws, 3)
    check(
        "el audio llega crudo al STT",
        FakeSttClient.sent_audio,
        [b"\x01\x02" * 480, b"\x03\x04" * 480],
    )
    check("'end' se reenvia al STT", FakeSttClient.end_calls, 1)
    check("y la sesion sigue traduciendo", [m.get("type") for m in messages], THREE_MESSAGES)

    print("\nsesion: frame desconocido no tumba la sesion")
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_text("basura que no es json")
            ws.send_text('{"type":"desconocido"}')
            ws.send_text('{"type":"text","text":"   "}')
            ws.send_text(TYPED_PHRASE)
            messages = read_exactly(ws, 3)
    check("la sesion sigue viva", [m.get("type") for m in messages], THREE_MESSAGES)

    print("\nsesion: la voz se muestra pero no se traduce sola")
    # El invariante central: el unico disparador de traduccion es el frame `text`
    # del cliente. Sin esto, una frase dictada se firmaria antes de que el
    # usuario confirme, que es justo lo que RF-STT-03 prohibe.
    FakeOrchestrator.calls = []
    FakeSttClient.incoming = [("hola, como estas", True)]
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            messages = read_exactly(ws, 1)
            check("el final de voz se reenvia", [m.get("type") for m in messages], ["transcript"])
            check("con su texto", messages[0].get("text"), "hola, como estas")
            check("y marcado como final", messages[0].get("final"), True)
            check("nada se firmo solo", FakeOrchestrator.calls, [])
            # Recién ahora, con la frase ya en la barra del cliente, se manda.
            ws.send_text(TYPED_PHRASE)
            tail = read_exactly(ws, 3)
    check("y la frase del cliente si se tradujo", FakeOrchestrator.calls, [PHRASE_TEXT])
    check("con sus oraciones", [m.get("type") for m in tail], THREE_MESSAGES)

    print("\nsesion: un final vacio es respuesta, no perdida")
    # Apagar el microfono manda `end`; el STT responde con un final vacio cuando
    # su filtro de descarte no encontro palabras. Sin reenviarlo, el cliente se
    # come su timeout y reporta como fallida una frase que nunca existio.
    FakeOrchestrator.calls = []
    FakeSttClient.incoming = [("hola", False), ("", True)]
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            messages = read_exactly(ws, 2)
            check("el parcial y el final vacio llegan", [m.get("type") for m in messages], ["transcript", "transcript"])
            check("el final va vacio", messages[1].get("text"), "")
            check("y como final", messages[1].get("final"), True)
            check("nada se intento traducir solo", FakeOrchestrator.calls, [])
            # La frase escrita al final demuestra que la sesion sigue viva.
            ws.send_text(TYPED_PHRASE)
            tail = read_exactly(ws, 3)
    check("y el cliente puede seguir mandando", [m.get("type") for m in tail], THREE_MESSAGES)

    print("\nsesion: el frame `mode` ya no existe")
    # La app de la rama de tiempo real mandaba `{"type":"mode",...}`. Esta
    # version ya no lo conoce y lo ignora como cualquier frame desconocido: lo
    # que decide que se traduzca es que mande la frase como `text`.
    FakeOrchestrator.calls = []
    with TestClient(build_app()) as client:
        with client.websocket_connect("/ws/translate") as ws:
            ws.send_text('{"type":"mode","mode":"dictation"}')
            ws.send_text('{"type":"mode","mode":"realtime"}')
            ws.send_text(TYPED_PHRASE)
            messages = read_exactly(ws, 3)
    check("no cambia nada", [m.get("type") for m in messages], THREE_MESSAGES)
    check("y solo se tradujo lo que se mando", FakeOrchestrator.calls, [PHRASE_TEXT])

    print()
    if failures:
        print(f"FALLARON {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("todo OK")


if __name__ == "__main__":
    main()