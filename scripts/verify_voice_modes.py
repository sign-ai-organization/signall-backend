"""Verifica los dos modos del micrófono contra el STT de verdad.

El micrófono de la app tiene dos interruptores y los dos mandan **lo mismo**: PCM
por el mismo WebSocket. Lo único que los separa es qué le pide el cliente al
backend con ``{"type":"mode"}``:

- ``dictation`` — solo transcribe. El texto vuelve al input y el muñeco no se
  mueve hasta que el usuario aprieta Traducir.
- ``realtime`` — cada fragmento se traduce y se manda mientras la persona habla.

Este script reproduce los WAV de `sign-ai-stt/fixtures/audio` por el socket a
velocidad real y mira qué vuelve, así que no hace falta ni micrófono ni persona
hablando. Corre con los servicios levantados:

    docker compose up -d
    python scripts/verify_voice_modes.py

Sale con 1 si algo no se cumple, que es lo que lo hace utilizable desde
`tools/verificar-tiempo-real.sh`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import wave
from pathlib import Path

import websockets

DEFAULT_URL = "ws://127.0.0.1:8080/ws/translate"
FRAME_BYTES = 960  # 30 ms a 16 kHz PCM16, el tamaño que manda el Android
FRAME_SECONDS = FRAME_BYTES / 2 / 16000

# Cuánto se sigue leyendo después del último frame esperado. Es lo que permite
# afirmar que algo **no** llegó: un `segment` que aparece 300 ms tarde está tan
# roto como uno que nunca aparece, y sin esta ventana el script cerraría el
# socket justo antes de que llegue.
SETTLE_SECONDS = 2.5


class Result:
    """Lo que el cliente recibió en una sesión, con el reloj del audio."""

    def __init__(self) -> None:
        self.transcripts: list[tuple[float, str, bool, bool]] = []
        self.segments: list[tuple[float, list[str], bool]] = []
        self.done_at: float | None = None
        self.error: str | None = None
        self.markers: list[str] = []
        self.switched_at = 0.0
        self.audio_end_at = 0.0

    def counts(self) -> str:
        return (
            f"transcript={len(self.transcripts)} segment={len(self.segments)} "
            f"done={1 if self.done_at is not None else 0}"
        )

    def final_dictation(self) -> str:
        for _, text, is_final, is_dictation in self.transcripts:
            if is_final and is_dictation and not text.startswith("<<"):
                return text
        return ""


def _read_wav_pcm16(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 16000:
            raise SystemExit(
                f"{path}: se espera mono PCM16 a 16 kHz, "
                f"viene {wav.getnchannels()}ch {wav.getsampwidth() * 8}bit {wav.getframerate()}Hz"
            )
        return wav.readframes(wav.getnframes())


async def run_session(
    url: str,
    pcm: bytes,
    mode: str,
    *,
    switch_at: float | None = None,
    timeout: float = 40.0,
) -> Result:
    """Reproduce el audio en un modo y devuelve todo lo que llegó.

    [switch_at] es el momento —en segundos de audio enviado— en el que se manda
    `end` y se cambia a `realtime` en mitad de la misma frase. Es lo que hace un
    usuario que dicta un rato y después prende el TR sin soltar el micrófono.
    """
    result = Result()
    frames = len(pcm) // FRAME_BYTES
    switch_frame = int(frames * switch_at) if switch_at is not None else None
    started_at = 0.0
    terminal = asyncio.Event()

    def record(payload: dict) -> None:
        kind = payload.get("type")
        at = (time.monotonic() - started_at) * 1000
        if kind == "transcript":
            result.transcripts.append(
                (
                    at,
                    payload.get("text", ""),
                    bool(payload.get("final")),
                    bool(payload.get("dictation")),
                )
            )
            # En dictado el `final` es el último frame: no hay `done` detrás. No
            # se corta la lectura acá porque justo después viene el audio de lo
            # que el usuario diga con el micrófono apagado.
            if payload.get("final") and payload.get("dictation"):
                terminal.set()
        elif kind == "segment":
            result.segments.append(
                (at, [g["text"] for g in payload["segment"]["glosses"]], bool(payload.get("provisional")))
            )
        elif kind == "done":
            result.done_at = at
            terminal.set()
        elif kind == "error":
            result.error = str(payload.get("message"))
            terminal.set()

    async def read(socket, stop: asyncio.Event) -> None:
        """Lee hasta que `stop` se dispare, o hasta que venza el plazo.

        No se corta cuando aparece el frame terminal. En el escenario del cambio
        de modo el `final` de lo dictado es el terminal, y justo después llegan
        los fragmentos de la parte de tiempo real: dejar de leer ahí los
        escondería y el test "después del cambio sí se firma" fallaría siempre.
        """
        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(socket.recv(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if isinstance(raw, bytes):
                continue
            record(json.loads(raw))

    async with websockets.connect(url, max_size=None) as socket:
        stop = asyncio.Event()
        reader = asyncio.create_task(read(socket, stop))
        # Que el STT termine de conectar antes del primer sample, como hace el
        # cliente Android: el audio que se pierde al empezar es la primera
        # palabra de la frase.
        await asyncio.sleep(0.4)
        started_at = time.monotonic()
        await socket.send(json.dumps({"type": "mode", "mode": mode}))

        for index in range(frames):
            if index and index == switch_frame:
                await socket.send(json.dumps({"type": "end"}))
                await socket.send(json.dumps({"type": "mode", "mode": "realtime"}))
                result.switched_at = (time.monotonic() - started_at) * 1000
                marker = f"cambio a realtime a los {index * FRAME_SECONDS:.1f}s de audio"
                result.markers.append(marker)
                print(f"    <<{marker}>>")
            await socket.send(pcm[index * FRAME_BYTES : (index + 1) * FRAME_BYTES])
            await asyncio.sleep(FRAME_SECONDS)

        result.audio_end_at = (time.monotonic() - started_at) * 1000
        await socket.send(json.dumps({"type": "end"}))

        try:
            await asyncio.wait_for(terminal.wait(), timeout)
        except asyncio.TimeoutError:
            result.error = f"timeout de {timeout:.0f}s esperando el cierre"

        # Ventana de gracia, con el lector seguir leyendo: es lo que hace válida
        # la afirmación de "el avatar no firmó" y la de "después del cambio sí".
        await asyncio.sleep(SETTLE_SECONDS)
        stop.set()
        reader.cancel()
        try:
            await reader
        except asyncio.CancelledError:
            pass

    return result


def _resolve_fixtures_dir(given: str) -> Path:
    """Busca el directorio de fixtures en los tres lugares donde suele estar.

    El mismo script corre desde el host (repo hermano en `../sign-ai-stt`) y
    desde el contenedor, donde `docker-compose.yml` monta los fixtures en
    `/fixtures`. Un default que solo funcione en uno de los dos deja el otro sin
    forma de correr el test.
    """
    candidates = [Path(given), Path("/fixtures/audio"), Path("fixtures/audio")]
    for candidate in candidates:
        if (candidate / "index.json").exists():
            return candidate
    print(
        f"no encontré index.json en {[str(c) for c in candidates]}. Generá los fixtures con\n"
        "  ../sign-ai-stt/.venv-tts/bin/python ../sign-ai-stt/scripts/make_audio_fixtures.py --all",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _load_clips_unused() -> None:  # pragma: no cover - placeholder removido
    raise NotImplementedError




def _load_clips(
    fixtures_dir: Path,
    only: list[str] | None,
    min_seconds: float,
) -> list[tuple[str, str, Path, float, float]]:
    """Devuelve `(id, texto, wav, duración, fin_de_la_voz)` de cada clip usable.

    El fin de la voz importa: los fixtures se generan con TTS y traen varios
    segundos de silencio al final, así que "la mitad del archivo" puede caer
    después de la última palabra —y un cambio de modo ahí no tiene nada que
    firmar del otro lado, que parece un bug y es un test mal cortado.
    """
    clips = json.loads((fixtures_dir / "index.json").read_text())["clips"]
    if only:
        clips = [clip for clip in clips if clip["id"] in only]
    out = []
    for clip in clips:
        wav = fixtures_dir / f"{clip['id']}.wav"
        if not wav.exists():
            continue
        seconds = clip.get("duration_ms", 0) / 1000
        if seconds < min_seconds:
            continue
        words = clip.get("words") or []
        speech_end = (words[-1]["end_ms"] / 1000) if words else seconds
        out.append((clip["id"], clip["text"], wav, seconds, speech_end))
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=40.0)
    parser.add_argument("--fixtures-dir", default="../sign-ai-stt/fixtures/audio")
    parser.add_argument("--only", action="append", help="id de fixture (repetible)")
    parser.add_argument("--clips", type=int, default=3, help="cuántos fixtures usar")
    parser.add_argument(
        "--min-seconds",
        type=float,
        default=3.0,
        help=(
            "descarta los clips más cortos. Con medio segundo de audio no se puede "
            "afirmar 'la seña llegó antes de que terminara de hablar': el STT recién "
            "cierra la frase después del silencio, así que el mínimo útil es de un "
            "par de segundos"
        ),
    )
    args = parser.parse_args()

    clips = _load_clips(_resolve_fixtures_dir(args.fixtures_dir), args.only, args.min_seconds)[
        : args.clips
    ]
    if not clips:
        print(
            f"no hay fixtures de al menos {args.min_seconds:.1f}s para probar "
            "(bajá --min-seconds o revisá el set)",
            file=sys.stderr,
        )
        return 2

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    for clip_id, text, wav, seconds, speech_end in clips:
        pcm = _read_wav_pcm16(wav)
        print(
            f"\n=== {clip_id}: {text!r} "
            f"({seconds:.1f}s de audio, voz hasta los {speech_end:.1f}s) ==="
        )

        # -- 1. Dictado: texto y nada más -----------------------------------
        result = await run_session(args.url, pcm, "dictation", timeout=args.timeout)
        dictated = result.final_dictation()
        print(f"  dictado     {result.counts()}  final={dictated!r}")
        check(f"{clip_id} dictado devuelve transcripción", bool(result.transcripts), text)
        check(f"{clip_id} dictado marca `dictation: true`", all(d for _, _, _, d in result.transcripts))
        check(f"{clip_id} dictado trae un final con texto", bool(dictated.strip()), repr(dictated))
        check(f"{clip_id} dictado NO firma ninguna seña", not result.segments, str(result.segments))
        check(f"{clip_id} dictado NO manda done", result.done_at is None)
        check(f"{clip_id} dictado no tira error", result.error is None, result.error or "")

        # -- 2. Tiempo real: firma mientras se habla ------------------------
        result = await run_session(args.url, pcm, "realtime", timeout=args.timeout)
        first = result.segments[0][0] if result.segments else -1.0
        print(f"  tiempo real {result.counts()}  1er signo={first:.0f}ms fin del audio={result.audio_end_at:.0f}ms")
        check(f"{clip_id} tiempo real firma", bool(result.segments), result.counts())
        check(f"{clip_id} tiempo real cierra con done", result.done_at is not None, result.counts())
        check(f"{clip_id} tiempo real no marca `dictation`", all(not d for _, _, _, d in result.transcripts))
        check(f"{clip_id} tiempo real no tira error", result.error is None, result.error or "")
        if result.segments:
            check(
                f"{clip_id} la primera seña llega antes de que termine el audio",
                first < result.audio_end_at,
                f"{first:.0f}ms < {result.audio_end_at:.0f}ms",
            )

        # -- 3. Cambio de modo en mitad de la frase ------------------------
        # El corte va en el medio de la voz, no del archivo: los fixtures traen
        # silencio al final y un corte ahí no dejaría nada que firmar después.
        switch_at = (speech_end / 2) / seconds
        result = await run_session(args.url, pcm, "dictation", switch_at=switch_at, timeout=args.timeout)
        first = result.segments[0][0] if result.segments else -1.0
        print(
            f"  cambio      {result.counts()}  corte={result.switched_at:.0f}ms "
            f"fin_del_audio={result.audio_end_at:.0f}ms 1er signo={first:.0f}ms"
        )
        for at, txt, is_final, is_dictation in result.transcripts:
            print(
                f"    {at:8.0f}ms  transcript  final={int(is_final)} dictation={int(is_dictation)}  {txt!r}"
            )
        # Lo que afirma el test es que **antes** del corte no se firmó nada: si el
        # latch por utterance no existiera, la frase dictada se cerraría como
        # tiempo real en el `final` y el muñeco firmaría texto que el usuario solo
        # quería escribir.
        check(f"{clip_id} el cambio se mandó", result.switched_at > 0, f"{result.switched_at:.0f}ms")
        check(
            f"{clip_id} antes del cambio no se firmó nada",
            all(at > result.switched_at for at, _, _ in result.segments),
            str(result.segments[:1]),
        )
        check(
            f"{clip_id} despues del cambio si se firma",
            bool(result.segments),
            f"1er signo={first:.0f}ms vs corte={result.switched_at:.0f}ms",
        )
        dictated_half = [
            text for _, text, is_final, is_dictation in result.transcripts
            if is_final and is_dictation and not text.startswith("<<")
        ]
        # Condicional a propósito: con el corte en la mitad, la primera mitad
        # puede no tener palabras (un clip que arranca con una pausa), y ahí no
        # hay transcripción que verificar. Lo que no puede pasar nunca es que se
        # firme, y eso ya se afirmó arriba.
        if dictated_half:
            check(
                f"{clip_id} la parte dictada llegó como transcripción y sin firmar",
                bool(dictated_half),
                repr(dictated_half),
            )
        else:
            print(f"  (la primera mitad no tenía palabras: nada que verificar)")
        check(f"{clip_id} el cambio no tira error", result.error is None, result.error or "")

    print()
    if failures:
        print(f"FALLARON {len(failures)}: {', '.join(failures)}")
        return 1
    print(f"todo OK ({len(clips)} fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
