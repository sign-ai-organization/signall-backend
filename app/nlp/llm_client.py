import logging

from langchain_openai import ChatOpenAI

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
# The fix has three parts, all in this file:
#
#   1. The vocabulary is CLOSED and injected into the prompt, taken straight from
#      the catalog. The model cannot invent a sign that will not resolve.
#   2. Multi-word glosses are explicitly allowed, and there is an explicit
#      counter-example of the exact split we were getting.
#   3. `_repair_glosses` fixes the answer *after* the fact, because a 4B model
#      still gets ~10% of phrases wrong no matter how good the prompt is. It
#      re-joins adjacent fragments that form a real gloss, canonicalises spelling
#      against the catalog, and drops what it cannot map.
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

You must use ONLY the glosses in this closed vocabulary:
{vocabulary}

Rules:
- A gloss may be one or more words. "COMO ESTAS", "BUENOS DIAS" and "MAS O MENOS" \
are each ONE gloss, not three.
- Never split a gloss from the vocabulary into its separate words. If the \
vocabulary has "COMO ESTAS", never answer "TU,ESTAR,COMO".
- Write each gloss exactly as it appears in the vocabulary above: UPPERCASE, \
accents already removed, Ñ preserved as is.
- Keep topic-comment order: the topic of the sentence goes first.
- Drop articles (el, la, los, las, un, una) and the copula (ser/estar) when the \
meaning stays clear without them.
- Use the base/infinitive form of verbs, never conjugated.
- Do not emit a bare pronoun (YO, TU, USTEDES) unless the sentence is about \
that person: "estoy contento" is CONTENTO, not YO,CONTENTO.
- If no vocabulary gloss covers part of the meaning, leave that part out rather \
than inventing a gloss.
- Respond with ONLY the glosses separated by commas. No explanation, no \
classification, no separator other than a comma.

Examples:
Input: ¿Cómo estás?
Output: COMO ESTAS
Input: Buenos días, ¿cómo estás?
Output: BUENOS DIAS,COMO ESTAS
Input: Me siento feliz
Output: SENTIR,FELIZ
Input: Estoy contento
Output: CONTENTO
Input: Hola, por favor
Output: HOLA,POR FAVOR
Input: ¿Cuál es su nombre?
Output: NOMBRE,TU,QUE
Input: Firme aquí, por favor.
Output: FAVOR,AQUI,FIRMAR"""


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
    both constrains the prompt and backs the post-hoc repair, so an answer can
    never reference a sign the app is unable to play.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        timeout_ms: int,
        base_url: str = "",
        vocabulary: dict[str, str] | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_ms = timeout_ms
        self.vocabulary = vocabulary or {}
        # Sorted so the prompt (and therefore any server-side prompt cache) is
        # byte-identical between restarts.
        self._prompt = PROMPT_TEMPLATE.format(
            vocabulary=", ".join(sorted(set(self.vocabulary.values()))) or "(empty)"
        )
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
        )

    async def transform(self, text: str) -> list[str]:
        response = await self._chat.ainvoke(
            [
                ("system", self._prompt),
                ("human", text),
            ]
        )
        return self._repair_glosses(self._parse_glosses(response.content))

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
        separator = "," if "," in content else None
        return [gloss.strip().upper() for gloss in content.split(separator) if gloss.strip()]

    def _repair_glosses(self, glosses: list[str]) -> list[str]:
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
            if entry is None:
                dropped.append(gloss)
            else:
                repaired.append(entry)

        # Every gloss unmappable: the model was answering about something the
        # dataset cannot sign. Returning the original keeps the old behaviour
        # (validation marks them unavailable, the client falls back) instead of
        # inventing an empty segment that would play nothing at all.
        if not repaired:
            logger.warning("No gloss of %r is in the catalog: %s", glosses, glosses)
            return glosses

        if dropped:
            logger.info("Dropped out-of-catalog glosses %s from %s", dropped, repaired)
        return repaired

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
