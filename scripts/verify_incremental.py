"""Prueba de la lógica incremental sin levantar nada.

`IncrementalTranslator` es donde se decide qué seña se firma y cuál no, y esa
decisión es la parte difícil del trabajo en tiempo real. Probarlo por el WebSocket
real requiere Whisper, Neon y un modelo, o sea tres minutos por caso y ningún
aislamiento. Aquí se le pasan hipótesis con timestamps a mano y se chequea que:

- solo se traduce la cola nueva, nunca lo ya firmado;
- una corrección del STT sobre palabras ya firmadas no rompe el estado;
- sin timestamps se firman las palabras menos las que se están formando;
- un fragmento de una palabra no dispara una traducción por sílaba.

    python scripts/verify_incremental.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.models import Gloss, PhraseType, ValidatedSegment
from app.realtime.incremental import IncrementalTranslator, TranscriptUpdate


def fake_translate(text: str) -> ValidatedSegment:
    """Traduce de mentira: mayúsculas y un guion, como glosa.

    Lo importante es que registre qué se le pidió, no que acierte la traducción.
    """
    return ValidatedSegment(
        type=PhraseType.AFFIRMATIVE,
        glosses=[Gloss(text=word.upper(), available=True) for word in text.split()],
    )


async def transcript(
    text: str,
    final: bool = False,
    *,
    audio_ms: float | None = None,
    word_ms: float = 300.0,
) -> TranscriptUpdate:
    """Construye una actualización con timestamps coherentes con `text`.

    Cada palabra dura `word_ms` y hay 100 ms de hueco entre una y otra, así que
    `end_ms` de la palabra i es `(i+1) * word_ms - 100`. El audio capturado
    termina donde termina la última palabra, más un pequeño margen.
    """
    words = tuple(
        (word, index * word_ms, (index + 1) * word_ms - 100.0)
        for index, word in enumerate(text.split())
    )
    end = audio_ms if audio_ms is not None else (len(words) * word_ms if words else 0.0)
    return TranscriptUpdate(text=text, final=final, words=words, audio_ms=end)


async def check(name: str, condition: bool, detail: str = "") -> bool:
    mark = "ok  " if condition else "FALLA"
    print(f"  [{mark}] {name}{(' — ' + detail) if detail and not condition else ''}")
    return condition


async def main() -> int:
    passed = True

    # ---------------------------------------------------------------- caso 1
    print("\n1. Solo se traduce la cola nueva")
    calls: list[str] = []
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    # El helper `transcript` deja `audio_ms` justo en el final de la última
    # palabra, así que con margen de 180 ms la última palabra nunca queda firme
    # hasta que llega el `final`. Por eso la primera hipótesis no firma nada:
    # es lo correcto, y es lo que evita firmar una palabra que después cambia.
    chunks = await translator.update(await transcript("hola"))
    passed &= await check("la primera hipótesis no firma nada", calls == [], f"llamadas={calls}")

    chunks += await translator.update(await transcript("hola como"))
    chunks += await translator.update(await transcript("hola como estas"))
    chunks += await translator.update(await transcript("hola como estas bien", final=True))

    passed &= await check(
        "no se re-traduce lo ya firmado",
        calls == ["hola", "como", "estas bien"],
        f"llamadas={calls}",
    )
    passed &= await check("un fragmento por firma", len(chunks) == 3, f"chunks={len(chunks)}")
    passed &= await check("índices correlativos", [c.index for c in chunks] == [0, 1, 2])
    passed &= await check(
        "el último fragmento no es provisional",
        [c.provisional for c in chunks] == [True, True, False],
        f"provisional={[c.provisional for c in chunks]}",
    )
    passed &= await check(
        "el texto de origen viaja con el fragmento",
        [c.source_text for c in chunks] == ["hola", "como", "estas bien"],
        f"fuentes={[c.source_text for c in chunks]}",
    )

    # ---------------------------------------------------------------- caso 2
    print("\n2. Una corrección del STT sobre texto ya firmado no rompe nada")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    await translator.update(await transcript("me llamo ana"))
    calls.clear()
    # El STT cambió "llamo" por "llamo" con signo distinto; lo firmado no se toca.
    await translator.update(await transcript("me llamas ana", final=True))

    passed &= await check(
        "solo se traduce la palabra nueva",
        calls == ["ana"],
        f"llamadas={calls}",
    )
    passed &= await check("el estado no retrocedió", translator.segments_sent == 2, f"n={translator.segments_sent}")

    # ---------------------------------------------------------------- caso 3
    print("\n3. La última palabra espera a que deje de formarse")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    # audio_ms apenas pasa el final de "hola": el margen todavía no se cumplía.
    await translator.update(
        TranscriptUpdate(text="hola", final=False, words=(("hola", 0.0, 300.0),), audio_ms=380.0)
    )
    passed &= await check("nada aún con la palabra al borde", calls == [], f"llamadas={calls}")

    await translator.update(
        TranscriptUpdate(text="hola", final=False, words=(("hola", 0.0, 300.0),), audio_ms=700.0)
    )
    passed &= await check("firma cuando el margen se cumple", calls == ["hola"], f"llamadas={calls}")

    # ---------------------------------------------------------------- caso 4
    print("\n4. Sin timestamps se firman las palabras menos la última")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    await translator.update(TranscriptUpdate(text="hola", final=False))
    passed &= await check("una palabra sola no se firma", calls == [], f"llamadas={calls}")

    await translator.update(TranscriptUpdate(text="hola como"))
    passed &= await check("firma la primera de dos", calls == ["hola"], f"llamadas={calls}")

    await translator.update(TranscriptUpdate(text="hola como estas"))
    passed &= await check("firma la que ya no está al borde", calls == ["hola", "como"], f"llamadas={calls}")

    # ---------------------------------------------------------------- caso 5
    print("\n5. El agrupamiento evita una traducción por sílaba")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 3

    await translator.update(TranscriptUpdate(text="hola", final=False))
    await translator.update(TranscriptUpdate(text="hola como", final=False))
    passed &= await check("una palabra sigue sin disparar nada", calls == [], f"llamadas={calls}")

    await translator.update(TranscriptUpdate(text="hola como estas", final=False))
    passed &= await check(
        "tres palabras exactas todavía no alcanzan (falta una de margen)",
        calls == [],
        f"llamadas={calls}",
    )

    # Cuarta palabra: ya hay tres firmes y una formándose, que es exactamente
    # el caso que `batch_words=3` existe para no fragmentar.
    await translator.update(TranscriptUpdate(text="hola como estas bien", final=False))
    passed &= await check(
        "con batch=3 dispara de a tres palabras",
        calls == ["hola como estas"],
        f"llamadas={calls}",
    )

    calls.clear()
    await translator.update(TranscriptUpdate(text="hola como estas bien", final=True))
    passed &= await check("el final no se agrupa", calls == ["bien"], f"llamadas={calls}")

    # ---------------------------------------------------------------- caso 6
    print("\n6. Ruido que no cambia nada")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    await translator.update(await transcript("hola como"))
    # El STT repite la misma hipótesis con otra puntuación.
    await translator.update(await transcript("Hola COMO.", ))
    passed &= await check("la puntuación no dispara traducción", calls == ["hola"], f"llamadas={calls}")

    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context))
    translator._settle_margin_ms = 180
    translator._batch_words = 1
    await translator.update(await transcript("eh hola como"))
    passed &= await check(
        "los rellenos no cuentan como palabras",
        calls == ["hola"],
        f"llamadas={calls}",
    )

    calls.clear()
    await translator.update(TranscriptUpdate(text="   "))
    passed &= await check("texto vacío no hace nada", calls == [], f"llamadas={calls}")

    # ---------------------------------------------------------------- caso 7
    print("\n7. Freno de seguridad de fragmentos")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context), max_segments=3)
    translator._settle_margin_ms = 180
    translator._batch_words = 1

    # Siete hipótesis de 1 a 7 palabras. La primera no firma (su última palabra
    # no tiene silencio detrás), y a partir de ahí cada una firma la anterior:
    # 6 fragmentos en total.
    for index in range(1, 8):
        await translator.update(await transcript(" ".join(str(n) for n in range(index)), final=index == 7))

    passed &= await check(
        f"produce 6 fragmentos (tope 3)", translator.segments_sent == 6, f"n={translator.segments_sent}"
    )
    passed &= await check("should_emit corta en el tope", not translator.should_emit(3))
    passed &= await check("should_emit deja pasar antes del tope", translator.should_emit(2))

    # ---------------------------------------------------------------- caso 8
    print("\n8. El contexto acumula lo ya firmado")
    contexts: list[str] = []
    translator = IncrementalTranslator(
        lambda text, context="": _capture(contexts, text, context),
        settle_margin_ms=180,
        batch_words=1,
    )

    await translator.update(await transcript("hola"))
    await translator.update(await transcript("hola como"))
    await translator.update(await transcript("hola como estas"))
    await translator.update(await transcript("hola como estas bien", final=True))

    passed &= await check("el primer fragmento no lleva contexto", contexts[0] == "", "")
    # Tres fragmentos en total (u2, u3, u4). El primero no lleva contexto; los
    # otros dos reciben lo firmado hasta ese momento.
    passed &= await check(
        "los siguientes sí, y es lo ya firmado",
        contexts[1:] == ["hola", "hola como"],
        f"contextos={contexts[1:]}",
    )
    passed &= await check(
        "el contexto no incluye el fragmento en curso",
        all("bien" not in context for context in contexts[1:]),
    )

    # ---------------------------------------------------------------- caso 9
    print("\n9. Un fragmento que es solo gramática no se firma")
    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context), settle_margin_ms=180)

    # "me" a secas hizo que el modelo respondiera YO, que no es lo que significa.
    # El primer update deja "me" firme y "vivo" formándose; el segundo lo cierra.
    await translator.update(await transcript("me vivo"))
    passed &= await check('"me" no produce una seña', calls == [], f"llamadas={calls}")
    await translator.update(await transcript("me vivo", final=True))
    passed &= await check("el resto de la frase sí", calls == ["vivo"], f"llamadas={calls}")
    passed &= await check(
        "el fragmento omitido igual queda en el contexto",
        translator._state.context == "me vivo",
        f"contexto={translator._state.context!r}",
    )

    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context), settle_margin_ms=180)
    # Un fragmento mixto no se parte: "vivo en" conserva el "en".
    await translator.update(await transcript("vivo en", final=True))
    passed &= await check("un fragmento mixto no se descompone", calls == ["vivo en"], f"llamadas={calls}")

    calls.clear()
    translator = IncrementalTranslator(lambda text, context="": _record(calls, text, context), settle_margin_ms=180)
    # "como" y "mas" son glosas del catálogo: filtrarlas rompería "como estas"
    # y "mas o menos".
    await translator.update(await transcript("como estas", final=True))
    passed &= await check("las glosas del catálogo no se filtran", calls == ["como estas"], f"llamadas={calls}")

    print("\n" + ("todo ok" if passed else "HAY FALLAS"))
    return 0 if passed else 1


async def _capture(contexts: list[str], text: str, context: str = "") -> ValidatedSegment:
    contexts.append(context)
    return fake_translate(text)


async def _record(calls: list[str], text: str, context: str = "") -> ValidatedSegment:
    calls.append(text)
    return fake_translate(text)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))