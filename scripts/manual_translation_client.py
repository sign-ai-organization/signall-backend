"""Manual, real-microphone test of the full translation session
(/ws/translate): captures your voice, streams it to OUR backend (not
directly to the STT service), and prints whatever comes back — the final
translated result, or an error message. With DEBUG_TRACE_ENABLED=true on
the backend, it also prints the per-step pipeline timings.

Requires requirements-dev.txt (sounddevice) installed.

Usage: python -m scripts.manual_translation_client [ws_url]
(default ws_url: ws://127.0.0.1:8080/ws/translate)
"""

import asyncio
import json
import sys
import time

import numpy as np
import sounddevice as sd
import websockets

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

URL = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8080/ws/translate"


def print_trace(trace: dict) -> None:
    print(f"[traza] fuente: {trace['source']}")
    steps_ms = trace["steps_ms"]
    name_width = max((len(name) for name in steps_ms), default=0)
    for name, ms in steps_ms.items():
        print(f"    {name:<{name_width}}  {ms:>8.1f} ms")
    print()


async def main() -> None:
    audio_queue: "asyncio.Queue[bytes]" = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        pcm16 = (np.clip(indata[:, 0] * 32768, -32768, 32767)).astype(np.int16)
        loop.call_soon_threadsafe(audio_queue.put_nowait, pcm16.tobytes())

    async with websockets.connect(URL, ping_interval=None) as ws:
        print(f"Conectado a {URL}. Hablá por el micrófono (Ctrl+C para salir)...\n")

        async def sender():
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=FRAME_SIZE,
                callback=callback,
            ):
                while True:
                    chunk = await audio_queue.get()
                    await ws.send(chunk)

        async def receiver():
            processing_started_at = None

            async for message in ws:
                data = json.loads(message)

                if isinstance(data, dict) and data.get("type") == "transcript":
                    if data["final"]:
                        if not data["text"].strip():
                            continue
                        print(f"\n[TEXTO FINAL] {data['text']!r}")
                        print("[procesando...]")
                        processing_started_at = time.perf_counter()
                    else:
                        print(f"\n[texto parcial] {data['text']!r}")
                    continue

                if isinstance(data, dict) and data.get("type") == "trace":
                    print_trace(data)
                    continue

                elapsed = (
                    f" ({time.perf_counter() - processing_started_at:.2f}s)"
                    if processing_started_at is not None
                    else ""
                )
                processing_started_at = None

                if isinstance(data, dict) and data.get("type") == "error":
                    print(f"\n[ERROR]{elapsed} {data['message']}\n")
                    continue

                print(f"\n[RESULTADO]{elapsed}")
                for segment in data:
                    print(f"  type={segment['type']}")
                    for gloss in segment["glosses"]:
                        print(f"    {gloss}")

        try:
            await asyncio.gather(sender(), receiver())
        except websockets.exceptions.ConnectionClosed as exc:
            print(f"\n[conexión cerrada] {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nFinalizando...")
