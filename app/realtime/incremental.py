"""Traducción incremental: de una transcripción que crece, a señas que salen.

El problema concreto
--------------------

El STT no entrega una frase, entrega una hipótesis que va creciendo:

    "hola"  ->  "hola como"  ->  "hola como estas"  ->  "hola como estas bien"

Traducir cada una de esas hipótesis entera produce trabajo duplicado y una
salida incoherente: el avatar firmaría HOLA, después HOLA COMO, después HOLA
COMO ESTAS, y el usuario vería la misma seña tres veces.

Lo que hace este módulo
----------------------

Mantiene, por utterance, qué parte de la hipótesis ya se Becó una decisión
irreversible (glosas enviadas al cliente) y traduce **solo el tramo nuevo**.

La regla que decide qué es "nuevo" son los timestamps por palabra que manda el
STT (`app/session.py`, campo `words`): una palabra está firme cuando su final
está al menos `settle_margin_ms` antes del final del audio capturado. Eso
responde una pregunta que el texto solo no puede responder: *¿esta persona ya
terminó de decir "estas", o todavía la está formando?*

Sin timestamps hay un plan B (`Plan B: sin timestamps` abajo) que usa una
heurística. Es peor, y por eso los timestamps son el camino principal.
"""

import logging
import re
from dataclasses import dataclass, field

from app.domain.models import ValidatedSegment
from app.observability.pipeline_trace import trace_step

logger = logging.getLogger(__name__)

# Palabras que el STT repite y que no aportan nada a la seña. Filtrarlas en el
# borde evita que una hipótesis "hmm hmm hola" se traduzca como frase rara y,
# sobre todo, que el índice de palabras firmadas no avance: sin esto, el
# prefijo común se queda trabado y el resto de la frase nunca se firma.
#
# `_tokenize` y `_settled_count` aplican exactamente el mismo filtro. Si uno
# contara "eh" y el otro no, el conteo de palabras firmes se desalinea del
# índice del token y se firma media palabra de más.
_FILLERS = frozenset(
    {"eh", "ah", "ehh", "ahh", "mmm", "hmm", "um", "uh", "este", "esta", "eso", "aqui", "alla"}
)

# Todo lo que no es palabra ni espacio se va. Se conserva `¿?` porque el STT los
# escribe y el `GlossAnalyzer` los usa para clasurar la frase.
_PUNCTUATION_RE = re.compile(r"[^\w\s¿?]", re.UNICODE)


def _is_kept(word: str) -> bool:
    """Si la palabra cuenta para el conteo de palabras firmadas."""
    return bool(word) and word not in _FILLERS


# Palabras-functional-words que no tienen glosa propia en LSC50 ni forman parte de
# una glosa frasal. La lista es **deliberadamente corta**: solo entra lo que
# claramente no aporta una seña.
#
# Lo que NO entra es igual de importante. "como", "donde", "cuando", "que" y "mas"
# son glosas del catálogo (COMO, DONDE, CUANDO, QUE) o parte de una frasal (MAS O
# MENOS), así que filtrarlas rompería frases que hoy funcionan. Quitar la "o" de
# "más o menos" deja "más menos", que es justo el error que el prompt de glosas
# frasales vino a arreglar.
#
# Y el filtro es de todo-o-nada: solo se descarta un fragmento cuando **todas**
# sus palabras son funcionales. Un fragmento mixto ("vivo en") se traduce entero,
# porque partirlo exigiría morphology que acá no hay.
_FUNCTION_WORDS = frozenset(
    {
        # artículos
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        # preposiciones
        "a", "al", "de", "del", "con", "en", "por", "para", "sin", "sobre", "entre",
        # conjunciones
        "y", "o", "u", "e", "ni", "pero",
        # pronombres objeto
        "me", "te", "se", "nos", "os", "lo", "le", "les",
        # auxiliares y verbos sin glosa en LSC50
        "es", "son", "soy", "eres", "esta", "estamos", "estan", "he", "ha", "hay",
        "fue", "era", "fui",
        # adverbios sin carga
        "muy", "tambien", "ya", "ahora", "hoy", "aqui", "alli",
    }
)


def _is_all_function_words(words: list[str]) -> bool:
    """Si el fragmento no tiene nada que firmar."""
    return bool(words) and all(word in _FUNCTION_WORDS for word in words)


@dataclass(frozen=True)
class TranscriptUpdate:
    """Una actualización de la transcripción que llega del STT."""

    text: str
    final: bool = False
    # `word` es la palabra como la escribió el STT; `start_ms` / `end_ms` son
    # relativos al inicio del buffer de audio que la produjo.
    words: tuple[tuple[str, float, float], ...] = ()
    # Duración del audio que el STT tenía capturado cuando generó esto.
    audio_ms: float = 0.0


@dataclass
class TranslationChunk:
    """Un fragmento listo para enviarse al cliente."""

    index: int
    segment: ValidatedSegment
    # Texto del que salió. Sirve para los logs y para que el cliente pueda
    # mostrar de dónde vino cada seña.
    source_text: str
    # `true` si este fragmento se calculó a partir de una hipótesis parcial y
    # podría refinarse. El cliente lo usa para no presentar un texto provisional
    # como definitivo.
    provisional: bool
    # Cuántas palabras nuevas trae. El cliente lo usa para decidir si un cambio de
    # glosas es material o solo un ajuste de puntuación.
    word_count: int = 0


@dataclass
class _CommitState:
    """Lo que ya se decidió de este utterance.

    `committed_words` es el prefijo de la hipótesis que ya produjo glosas. Es
   append-only a propósito: si el STT revisa una palabra que ya se firmó, no
    hay forma de "des-firmar" una seña que ya se está animando en pantalla, y
    re-firmarla sería peor que esperar el texto equivocado un instante.
    """

    words: list[str] = field(default_factory=list)
    # Todo lo firmado hasta ahora, en el texto del STT. Se le pasa al LLM como
    # contexto de solo lectura: sin él, un fragmento suelto ("estudiante") se
    # responde como si fuera la frase entera, y "me llamo ana / estudiante"
    # terminaba firmando NIÑO.
    context: str = ""
    segments_sent: int = 0
    settled_count: int = 0
    last_final_text: str | None = None


class IncrementalTranslator:
    """Decide qué parte de una transcripción creciente falta por traducir.

    No sabe nada de WebSockets ni de STT: recibe actualizaciones y devuelve
    listas de fragmentos. Eso lo hace verificable sin levantar el servicio
    entero, que es como lo cubren `scripts/verify_incremental.py`.
    """

    def __init__(
        self,
        translate_text,
        settle_margin_ms: int = 180,
        batch_words: int = 2,
        max_segments: int = 32,
    ) -> None:
        # `translate_text` es un callable asíncrono (texto, contexto) ->
        # ValidatedSegment. Se inyecta para no atar esta clase al Orchestrator y
        # para que la prueba pueda usar una función de mentira.
        self._translate_text = translate_text
        self._settle_margin_ms = settle_margin_ms
        self._batch_words = batch_words
        self._max_segments = max_segments
        self._state = _CommitState()

    def reset(self) -> None:
        """Empieza un utterance nuevo."""
        self._state = _CommitState()

    @property
    def segments_sent(self) -> int:
        return self._state.segments_sent

    async def update(self, update: TranscriptUpdate) -> list[TranslationChunk]:
        """Traduce lo nuevo de esta actualización y devuelve los fragmentos."""
        if not update.text.strip():
            return []

        tokens = self._tokenize(update.text)
        if not tokens:
            return []

        settled = self._settled_count(update, tokens)

        # El prefijo común no puede ser más corto que lo ya firmado: si el STT
        # corrigió algo atrás, seguimos desde donde ya estamos (ver
        # `_CommitState`). Nunca sobreescribimos `committed_words` hacia atrás.
        common = _common_prefix_len(self._state.words, tokens[:settled])
        if common < len(self._state.words):
            logger.debug(
                "STT revizó texto ya firmado: %r -> %r; se continúa desde la palabra %d",
                self._state.words,
                tokens[:settled],
                common,
            )
        start = max(common, len(self._state.words))

        if start >= settled:
            # Nada nuevo todavía: es el caso normal entre dos parciales.
            return []

        tail = tokens[start:settled]
        if not update.final and not update.words and len(tail) < self._batch_words:
            # Plan B: sin timestamps, no se firma hasta juntar un par de
            # palabras. Firmar de a una palabra produce una llamada al LLM por
            # sílaba, que es más lento que lo que ahorra.
            return []

        if _is_all_function_words(tail):
            # "me" a secas llegó a producir YO y "en" a producir DONDE: al modelo
            # un fragmento que es solo gramática no le queda nada a lo que
            # aferrarse y se agarra de la glosa más cercana. Las palabras se
            # marcan como vistas igual, así el contexto del siguiente fragmento
            # las incluye y no se vuelven a mirar.
            logger.info("fragmento %r es solo palabras funcionales: se omite", _detokenize(tail))
            self._commit(tokens, settled)
            return []

        source = _detokenize(tail)
        with trace_step("realtime.incremental"):
            segment = await self._translate_text(source, self._state.context)

        chunk = TranslationChunk(
            index=self._state.segments_sent,
            segment=segment,
            source_text=source,
            provisional=not update.final,
            word_count=len(tail),
        )
        self._commit(tokens, settled)
        self._state.segments_sent += 1

        logger.info(
            "fragmento %d: %r -> %s (provisional=%s)",
            chunk.index,
            source,
            [gloss.text for gloss in segment.glosses],
            chunk.provisional,
        )
        return [chunk]

    def _commit(self, tokens: list[str], settled: int) -> None:
        """Marca las palabras hasta `settled` como ya decididas.

        Append-only a propósito: una palabra firmada no se vuelve a mirar, ni
        siquiera si el STT después la corrige. Des-firmar una seña que ya se está
        animando en pantalla no es posible, y volver a firmarla sería peor que
        esperar un instante con el texto viejo.
        """
        self._state.words = tokens[:settled]
        self._state.settled_count = settled
        self._state.context = _detokenize(self._state.words)

    def _settled_count(self, update: TranscriptUpdate, tokens: list[str]) -> int:
        """Cuántas palabras de `tokens` se pueden considerar definitivas.

        Con timestamps: una palabra está firme cuando terminó
        `settle_margin_ms` antes del final del audio capturado. La última
        palabra del buffer casi nunca cumple eso —es la que se está formando— así
        que en la práctica esto firma "todo menos lo que se está diciendo".

        Sin timestamps y sin final: se firma todo menos la última palabra, que es
        la que el decodificador puede cambiar por completo.
        """
        if update.final:
            return len(tokens)

        if not update.words or update.audio_ms <= 0:
            # Plan B: una sola palabra queda fuera, la que se puede estar
            # formando todavía. El mínimo de palabras por fragmento lo aplica
            # `update`, no acá: son dos límites distintos y juntarlos hacía que
            # con `batch_words=3` una frase de tres palabras no firmara nada
            # hasta el final.
            return max(0, len(tokens) - 1)

        horizon = update.audio_ms - self._settle_margin_ms
        settled = 0
        for word_text, _start, end in update.words:
            # Solo cuentan las palabras que sobreviven a `_tokenize`. Contar
            # también las descartadas haría que `settled` fuera un índice en el
            # espacio de `words` usado para indexar `tokens`, y el desfase
            # firmaría palabras que todavía no se dijeron.
            if not _is_kept(word_text):
                continue
            if end <= horizon:
                settled += 1
            else:
                # Los timestamps de Whisper son monótonos en la práctica, pero
                # si alguna vez vinieran desordenados, cortar acá evita contar
                # como firmes palabras que aún no se dijeron.
                break

        return settled

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Parte en palabras comparables.

        Se comparan en minúsculas y sin puntuación porque el STT escribe
        "Buenos días." en un parcial y "buenos días" en el siguiente, y eso no es
        una revisión del contenido sino de la forma.
        """
        cleaned = _PUNCTUATION_RE.sub(" ", text.lower())
        return [word for word in cleaned.split() if _is_kept(word)]

    def should_emit(self, segments_sent: int) -> bool:
        """Freno de seguridad para un utterance que no cierra nunca.

        Un STT desarmado puede producir parciales indefinidamente. Firmar 500
        fragmentos en una sola frase no ayuda a nadie; después de
        `max_segments` se sigue traduciendo pero se deja de emitir hacia el
        cliente, que ya tiene con qué trabajar.
        """
        return segments_sent < self._max_segments


def _common_prefix_len(left: list[str], right: list[str]) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def _detokenize(words: list[str]) -> str:
    return " ".join(words)