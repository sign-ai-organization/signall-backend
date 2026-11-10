import logging
import re

from langchain_openai import ChatOpenAI

from app.metrics import metrics_timer
from app.nlp.gloss_lexicon import insert_implicit_pronoun, normalize_order, resolve_inflection
from app.validation.catalog_repository import normalize_gloss

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS PROMPT WAS REWRITTEN (2026-10-14)
# ─────────────────────────────────────────────────────────────────────────────
#
# The previous prompt said:
#
#     "A gloss is a single word representing one sign: UPPERCASE, ..."
#
# That rule is what broke the pipeline, and it is worth keeping the reasoning
# because the failure is silent.
#
# LSC50 (the dataset this app signs with) is NOT a word-per-sign vocabulary. It
# contains *phrasal* glosses: "COMO ESTAS", "BUENOS DIAS", "MAS O MENOS",
# "POR FAVOR". Telling the model "one gloss = one word" actively pushes it to
# shred those phrases, so for the input "cómo estás" it answered:
#
#     TÚ, ESTAR, CÓMO
#
# while the catalog already had the whole thing as "COMO ESTAS" (id 0026).
#
# Why that is worse than an obvious failure: "TÚ" is id 0039 and "CÓMO" is
# id 0044, and only ids 0000-0031 have an exported animation. "ESTAR" is not in
# the catalog at all. So every single gloss in that answer was unplayable, the
# avatar fell back to its default sign, and the app still reported "Reproducción
# completada". It looked like it worked.
#
# It was NOT the model's fault. Verified on 2026-10-14 by running the *same*
# old prompt against both models:
#
#     input "cómo estás"      gpt-4o-mini: TÚ,ESTAR,CÓMO
#                             qwen3:4b:   ESTÁS,CÓMO
#
# Both split. (qwen additionally broke the prompt's own accent/infinitive rules
# and emitted a typo, "FEELIZ".) Switching models does not fix this; only the
# prompt does.
#
# The fix has two parts, all in this file:
#
#   1. Multi-word glosses are explicitly allowed, and there is an explicit
#      counter-example of the exact split we were getting.
#   2. `_repair_glosses` fixes the answer *after* the fact, because a 4B model
#      still gets ~10% of phrases wrong no matter how good the prompt is. It
#      re-joins adjacent fragments that form a real gloss, canonicalises spelling
#      against the catalog, and drops what it cannot map.
#
# A third part used to live here: injecting the whole catalog into the prompt
# as a closed vocabulary, so the model could not answer with a sign that would
# not resolve. It is gone (decision D-7, owner, 2026-10-16): the list does not
# scale, it goes against the test plan, and the validator already marks a sign
# that is not in the catalog as unavailable. The vocabulary is still used, but
# only in memory, to repair the answer. See docs/performance.md section 9.
#
# Measured on 10 phrases with this prompt (2026-10-14):
#
#     model                 in-vocabulary   mean latency
#     gpt-4o-mini           9/10            1.09 s
#     qwen3:4b-instruct     9/10            0.20 s
#
# Quality is equivalent, so the local model is the default in .env (free,
# offline, and a thesis demo does not depend on an API key or on wifi).
# `LLM_BASE_URL` selects the provider; see the class docstring.
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """You translate short Spanish sentences into LSC (Lengua de \
Señas Colombiana) glosses.

Rules:
- A gloss may be one or more words. "COMO ESTAS", "BUENOS DIAS" and "MAS O MENOS" \
are each ONE gloss, not three.
- Never split a multi-word gloss into its separate words. If the gloss is \
"COMO ESTAS", never answer "TU,ESTAR,COMO".
- Write each gloss in UPPERCASE, with the accents already removed and Ñ \
preserved as is.
- Keep topic-comment order: the topic of the sentence goes first.
- Drop articles (el, la, los, las, un, una) and the copula (ser/estar) when the \
meaning stays clear without them.
- Use the base/infinitive form of verbs, never conjugated.
- Keep the pronoun (YO, TU, USTEDES) when the sentence has one: "estoy \
contento" is YO,CONTENTO.
- Do not add anything the sentence does not say: no pronouns, no question \
words, no greetings. "Mi hermano está feliz" is HERMANO,FELIZ, never \
TU,HERMANO,FELIZ.
- Do not drop a content word (nouns, verbs, adjectives, adverbs) to make the \
list shorter: only the articles and the copula are dropped.
- If you do not know the gloss for part of the meaning, leave that part out \
rather than inventing one.
- Respond with ONLY the glosses separated by commas. No explanation, no \
classification, no preamble, no closing period, no separator other than a \
comma.

Examples:
Input: ¿Cómo estás?
Output: COMO ESTAS
Input: Buenos días, ¿cómo estás?
Output: BUENOS DIAS,COMO ESTAS
Input: Me siento feliz
Output: YO,SENTIR,FELIZ
Input: Estoy contento
Output: YO,CONTENTO
Input: Hola, por favor
Output: HOLA,POR FAVOR
Input: ¿Dónde vive tu familia?
Output: DONDE,TU,FAMILIA,VIVIR
Input: Yo nunca como mucho.
Output: YO,NUNCA,COMER,MUCHO"""


# Markdown bullets, list numbering and wrapping quotes that models add around
# an answer without being asked. They are never part of a gloss.
_WRAPPING = "\"'`´“”‘’«»*•·-–—[]()"
_LIST_NUMBER = re.compile(r"^\s*\d+\s*[.)-]\s*")


def _clean_gloss(raw: str) -> str:
    """Normalise one chunk of the model's answer into a gloss candidate.

    Removes bullets, list numbering, wrapping quotes and the closing
    punctuation; keeps inner spaces (a gloss like "COMO ESTAS" is one gloss).
    """
    gloss = _LIST_NUMBER.sub("", raw.strip())
    # «Aquí están las glosas: HOLA, BUENOS DIAS» mete el preámbulo delante de la
    # primera glosa cuando el modelo no separa con salto de línea. Un dos puntos
    # nunca es parte de una glosa, así que se corta ahí.
    if ":" in gloss:
        gloss = gloss.rsplit(":", 1)[-1]
    gloss = gloss.strip().strip(_WRAPPING).strip()
    gloss = gloss.strip(".,;:!¡?¿…").strip()
    gloss = gloss.strip(_WRAPPING).strip()
    return " ".join(gloss.upper().split())



class LLMClient:
    """Glosses a sentence with an OpenAI-compatible chat endpoint.

    `base_url` picks the provider. Empty (the default) means OpenAI itself.
    Point it at any OpenAI-compatible server to run the same prompt locally:

        Ollama      http://host.docker.internal:11434/v1
        LM Studio   http://host.docker.internal:1234/v1
        vLLM        http://host.docker.internal:8000/v1

    From inside Docker on Linux, `host.docker.internal` only resolves if the
    service declares
`extra_hosts: ["host.docker.internal:host-gateway"]`, and the local server
has to be listening on an external interface (Ollama binds 127.0.0.1 by
    default; set OLLAMA_HOST=0.0.0.0:11434).

    `vocabulary` is the catalog's gloss list, folded key -> display spelling. It
    backs the post-hoc repair, which is what keeps an answer from referencing a
    sign the app is unable to play. It is **not** part of the prompt: decision
    D-7 (owner, 2026-10-16) took the closed list out of it, because the list
    does not scale and the validator already marks a sign that is not in the
    catalog as unavailable.

    `categories` is the same folded keys mapped to the catalog's semantic
    category (`verbo`, `sustantivo`, ...). It is optional and only used to put
    the verb where the corpus puts it (`gloss_lexicon.normalize_order`); without
    it the answer keeps the order the model gave.

    `timeout_ms` is the ceiling of a single call and `max_retries` how many
    times a failed call is tried again. Together they keep the answer inside
    the window the Android client waits for a phrase before it gives up on its
    own.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        timeout_ms: int,
        max_retries: int = 1,
        base_url: str = "",
        vocabulary: dict[str, str] | None = None,
        categories: dict[str, str] | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.vocabulary = vocabulary or {}
        self.categories = categories or {}
        # The prompt is a constant: it does not depend on the catalog. D-7
        # (owner, 2026-10-16) took the closed vocabulary out of it, so there is
        # nothing left to build at start-up, and nothing that has to be rebuilt
        # when the catalog changes.
        self._prompt = PROMPT_TEMPLATE
        # ChatOpenAI already accepted base_url; Settings never exposed one, so
        # the provider could not be changed without editing code. That is what
        # branch bab1cd8 attempted; this is the same idea, ported onto current
        # main instead of merged, because that branch predates debug tracing,
        # the DB keep-alive and the nested segmenter settings.
        self._chat = ChatOpenAI(
            api_key=api_key,
            base_url=base_url or None,
            model=model,
            temperature=temperature,
            timeout=timeout_ms / 1000,
            max_retries=max_retries,
        )

    async def transform(self, text: str) -> list[str]:
        # `rt_first_sign_ms` says when the first sentence went out and
        # `rt_sentence_delay_ms` repeats that clock for every sentence, but
        # neither says *why* one of them was late. Until this metric existed the
        # only trace of the model call was `PipelineTrace`, which needs
        # `DEBUG_TRACE_ENABLED=true` and a log to read, so the number that
        # decides whether this feels real time had no measurement of the stage
        # that actually costs it.
        with metrics_timer(
            "llm_ms",
            "Inference del modelo de lenguaje para una oracion",
            {"model": self.model},
        ):
            response = await self._chat.ainvoke(
                [
                    ("system", self._prompt),
                    ("human", text),
                ]
            )
        return self._repair_glosses(self._parse_glosses(response.content), text)

    def update_catalog(self, vocabulary: dict[str, str], categories: dict[str, str]) -> None:
        """Swap in a catalog that loaded after start-up (PR-RES-04).

        The backend can start while the database is down; the repair of the
        model's answer then has nothing to check against. When the catalog
        arrives later, this gives it to the running client without a restart.
        """
        self.vocabulary = vocabulary
        self.categories = categories

    async def warm_up(self) -> None:
        """One filler call, so the first real phrase does not pay for the load.

        With a local server the first inference pulls the model into memory:
        measured, 6.2 s against the 270-440 ms of the ones after it. Without
        this, the first phrase of the session pays six seconds and the rest run
        fine, which is the worst way to fail for a demo. Errors are ignored on
        purpose: the model server being down at start-up must not keep the
        service from starting, and the first real phrase will report it as what
        it is.
        """
        try:
            await self.transform("hola")
        except Exception:  # noqa: BLE001 - the warm-up is optional
            logger.warning("LLM warm-up failed; the first real phrase will pay the model load", exc_info=True)

    def _parse_glosses(self, content: str) -> list[str]:
        """Turn the model's answer into a list of glosses, tolerating formatting.

        The prompt asks for "comma-separated uppercase", but models drift: they
        answer one gloss per line, close the list with a period, add a preamble
        ("Aquí están las glosas:") or wrap everything in quotes. Those are
        formatting, not translation, and treating them as glosses made whole
        phrases come out as a single unplayable sign (measured on 2026-11-04:
        "HOLA. BUENOS DIAS. BIENVENIDO." became one gloss instead of three).

        What this does NOT do is split a two-word gloss: splitting only happens
        on separators the model was told to use (comma, semicolon, line break)
        or on sentence periods; spaces inside a gloss are left alone.
        """
        text = content.strip()
        if not text:
            return []

        # Separators the prompt asks for, plus the ones models actually use.
        text = text.replace("\r", "\n")
        if "," in text:
            pieces = text.split(",")
        elif ";" in text:
            pieces = text.split(";")
        elif "\n" in text:
            pieces = text.split("\n")
        else:
            # No explicit separator: sentences end with a period, and a gloss
            # never contains one. Split there so "HOLA. BUENOS DIAS." is two.
            pieces = re.split(r"(?<=[.!?…])\s+", text)
            if len(pieces) == 1:
                pieces = [text]

        glosses: list[str] = []
        for piece in pieces:
            gloss = _clean_gloss(piece)
            if not gloss:
                continue
            # A chunk that ends with ":" is a preamble, not a gloss.
            if piece.strip().endswith(":"):
                logger.info("Dropped preamble from the model answer: %r", piece.strip()[:80])
                continue
            glosses.append(gloss)
        return glosses

    def _repair_glosses(self, glosses: list[str], text: str) -> list[str]:
        """Map what the model said onto glosses that actually exist.

        No vocabulary means nothing to check against (e.g. tests), so the answer
        is passed through untouched.
        """
        if not self.vocabulary or not glosses:
            return glosses

        glosses = self._merge_fragments(glosses)

        repaired: list[str] = []
        dropped: list[str] = []
        for gloss in glosses:
            entry = self.vocabulary.get(normalize_gloss(gloss))
            if entry is not None:
                repaired.append(entry)
                continue

            # A gloss the catalog does not have verbatim may still be one it
            # has in a different inflection ("NINOS" for "NIÑO"). Try that
            # before treating it as several glosses glued together.
            entry = resolve_inflection(gloss, self.vocabulary)
            if entry is not None:
                logger.info("Resolved inflected gloss %r to catalog entry %r", gloss, entry)
                repaired.append(entry)
                continue

            # A gloss the catalog does not have may be several glosses glued
            # together ("HOLA BUENOS DIAS" with no commas). Splitting it is the
            # inverse of _merge_fragments and only succeeds when every word is
            # a catalog gloss, so it cannot invent vocabulary.
            pieces = self._split_into_glosses(gloss)
            if pieces:
                logger.info("Split out-of-catalog gloss %r into %s", gloss, pieces)
                repaired.extend(pieces)
            else:
                dropped.append(gloss)

        # Every gloss unmappable: the model was answering about something the
        # dataset cannot sign. Returning the original keeps the old behaviour
        # (validation marks them unavailable, the client falls back) instead of
        # inventing an empty segment that would play nothing at all.
        if not repaired:
            logger.warning("No gloss of %r is in the catalog: %s", glosses, glosses)
            return glosses

        if dropped:
            logger.info("Dropped out-of-catalog glosses %s from %s", dropped, repaired)

        return insert_implicit_pronoun(text, normalize_order(repaired, self.categories), self.vocabulary)

    def _split_into_glosses(self, gloss: str) -> list[str]:
        """Split a chunk that is really several glosses run together.

        "HOLA BUENOS DIAS" with no commas is one chunk but three signs. A
        greedy longest-match pass over the catalog puts it back together; it
        returns [] unless *every* word lands on a catalog gloss, so a chunk
        with a word the catalog does not have is left to the caller (which
        drops it, as before).
        """
        words = gloss.split()
        if len(words) < 2:
            return []
        out: list[str] = []
        index = 0
        while index < len(words):
            for end in range(len(words), index, -1):
                candidate = " ".join(words[index:end])
                entry = self.vocabulary.get(normalize_gloss(candidate))
                if entry is not None:
                    out.append(entry)
                    index = end
                    break
            else:
                return []
        return out

    def _merge_fragments(self, glosses: list[str]) -> list[str]:
        """Re-join adjacent single words that are really one phrasal gloss.

        This is the exact failure the old prompt caused: "COMO","ESTAS" when
        the catalog has "COMO ESTAS". A greedy left-to-right pass is enough —
        gloss lists are short, and a wrong join simply fails to resolve and
        falls through to the per-gloss check.
        """
        merged: list[str] = []
        index = 0
        while index < len(glosses):
            current = glosses[index]
            # Longest match first so a three-word gloss wins over its prefixes.
            for end in range(len(glosses), index, -1):
                candidate = " ".join(glosses[index:end])
                if normalize_gloss(candidate) in self.vocabulary:
                    if end - index > 1:
                        logger.info("Merged %s into catalog gloss %r", glosses[index:end], candidate)
                    merged.append(candidate)
                    index = end
                    break
            else:
                merged.append(current)
                index += 1
        return merged
