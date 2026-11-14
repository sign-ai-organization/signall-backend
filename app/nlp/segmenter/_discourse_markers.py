from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.text_normalizer import normalize

_ACCENTED = set("áéíóúÁÉÍÓÚ")


def is_interrogative(token: str, normalized: str, config: SentenceSegmenterSettings) -> bool:
    if normalized not in config.interrogative_words:
        return False
    if normalized in config.ambiguous_interrogatives_without_accent:
        return any(c in _ACCENTED for c in token)
    return True


def is_infinitive(normalized: str) -> bool:
    return len(normalized) > 3 and normalized.endswith(("ar", "er", "ir"))


def _closing_end(normalized: list[str], i: int, closings: list[list[str]]) -> int | None:
    """If a closing starts at position i, returns the position where it ends."""
    for closing in closings:
        if normalized[i:i + len(closing)] == closing:
            return i + len(closing)
    return None


def _word_count(normalized: list[str], start: int, end: int) -> int:
    return sum(1 for x in normalized[start:end] if x)


def _introduces_indirect_question(previous: str, config: SentenceSegmenterSettings) -> bool:
    return previous in config.indirect_question_introducers or (
        config.infinitive_introduces_indirect and is_infinitive(previous))


def _counts_away_from_start(normalized: list[str], i: int, end: int, last_cut: int,
                            config: SentenceSegmenterSettings) -> bool:
    """Away from the start of the fragment, only some closings count."""
    if i == last_cut:
        return True
    return " ".join(normalized[i:end]) in config.closings_anywhere


def _cut_after_closing(normalized: list[str], i: int, last_cut: int, closings: list[list[str]],
                       config: SentenceSegmenterSettings, total: int) -> int | None:
    """The position right after a unit closing that ends the fragment, or None."""
    if not config.cut_after_closing:
        return None
    end = _closing_end(normalized, i, closings)
    if end is None or not _counts_away_from_start(normalized, i, end, last_cut, config):
        return None
    if end >= total or normalized[end] in config.no_cut_after_closing_before:
        return None
    if _word_count(normalized, end, total) < config.min_words_per_side:
        return None
    return end


def _cut_before_marker(normalized: list[str], i: int, markers: list[list[str]]) -> tuple[int | None, int]:
    """The position of a cutting marker that starts at i, and how many words it spans."""
    for marker in markers:
        if normalized[i:i + len(marker)] == marker:
            return i, len(marker)
    return None, 1


def _cut_before_interrogative(tokens: list[str], normalized: list[str], i: int, last_cut: int,
                              config: SentenceSegmenterSettings,
                              indirect_in_fragment: bool) -> tuple[int | None, bool]:
    """The position to cut before an interrogative at i, if it opens a fragment.

    The second value says whether the fragment now holds an indirect question,
    which keeps the next interrogative with a coordinating conjunction attached.
    """
    if not config.cut_before_interrogative or not is_interrogative(tokens[i], normalized[i], config):
        return None, indirect_in_fragment

    previous = normalized[i - 1] if i > 0 else ""
    if tokens[last_cut].startswith("¿"):
        return None, indirect_in_fragment     # already a question: "¿Y usted cómo va?"
    if _introduces_indirect_question(previous, config):
        return None, True
    if previous not in config.question_prefixes:
        return i, indirect_in_fragment
    if indirect_in_fragment and previous in ("y", "o"):
        return None, indirect_in_fragment
    return i - 1, indirect_in_fragment


def _cuts_here(candidate: int, last_cut: int, normalized: list[str], total: int,
               config: SentenceSegmenterSettings) -> bool:
    if candidate <= last_cut:
        return False
    return (_word_count(normalized, last_cut, candidate) >= config.min_words_per_side
            and _word_count(normalized, candidate, total) >= config.min_words_per_side)


def split_by_markers(text: str, config: SentenceSegmenterSettings) -> list[str]:
    tokens = text.split()
    normalized = [normalize(t) for t in tokens]
    n = len(tokens)
    markers = sorted((m.split() for m in config.cut_markers), key=len, reverse=True)
    closings = sorted((c.split() for c in config.unit_closings), key=len, reverse=True)

    cuts: list[int] = []
    last_cut = 0
    indirect_in_fragment = False
    i = 0
    while i < n:
        end = _cut_after_closing(normalized, i, last_cut, closings, config, n)
        if end is not None:
            cuts.append(end)
            last_cut = end
            indirect_in_fragment = False
            i = end
            continue

        candidate, step = _cut_before_marker(normalized, i, markers)
        if candidate is None:
            candidate, indirect_in_fragment = _cut_before_interrogative(
                tokens, normalized, i, last_cut, config, indirect_in_fragment)

        if candidate is not None and _cuts_here(candidate, last_cut, normalized, n, config):
            cuts.append(candidate)
            last_cut = candidate
            indirect_in_fragment = False
        i += step

    bounds = [0] + cuts + [n]
    return [" ".join(tokens[a:b]) for a, b in zip(bounds, bounds[1:], strict=False)]
