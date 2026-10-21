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


def split_by_markers(text: str, config: SentenceSegmenterSettings) -> list[str]:
    tokens = text.split()
    normalized = [normalize(t) for t in tokens]
    n = len(tokens)
    markers = sorted((m.split() for m in config.cut_markers), key=len, reverse=True)
    closings = sorted((c.split() for c in config.unit_closings), key=len, reverse=True)

    def word_count(start: int, end: int) -> int:
        return sum(1 for x in normalized[start:end] if x)

    cuts: list[int] = []
    last_cut = 0
    indirect_in_fragment = False
    i = 0
    while i < n:
        step = 1
        candidate = None

        if config.cut_after_closing:
            end = _closing_end(normalized, i, closings)
            # Away from the start of the fragment, only some closings count.
            if (end is not None and i != last_cut
                    and " ".join(normalized[i:end]) not in config.closings_anywhere):
                end = None
            if (end is not None and end < n
                    and normalized[end] not in config.no_cut_after_closing_before
                    and word_count(end, n) >= config.min_words_per_side):
                cuts.append(end)
                last_cut = end
                indirect_in_fragment = False
                i = end
                continue

        for marker in markers:
            if normalized[i:i + len(marker)] == marker:
                candidate = i
                step = len(marker)
                break

        if candidate is None and config.cut_before_interrogative and \
                is_interrogative(tokens[i], normalized[i], config):
            previous = normalized[i - 1] if i > 0 else ""
            if tokens[last_cut].startswith("¿"):
                pass    # the fragment is already a question: "¿Y usted cómo va?"
            elif (previous in config.indirect_question_introducers
                  or (config.infinitive_introduces_indirect and is_infinitive(previous))):
                indirect_in_fragment = True
            elif previous in config.question_prefixes:
                if not (indirect_in_fragment and previous in ("y", "o")):
                    candidate = i - 1
            else:
                candidate = i

        if (candidate is not None and candidate > last_cut
                and word_count(last_cut, candidate) >= config.min_words_per_side
                and word_count(candidate, n) >= config.min_words_per_side):
            cuts.append(candidate)
            last_cut = candidate
            indirect_in_fragment = False
        i += step

    bounds = [0] + cuts + [n]
    return [" ".join(tokens[a:b]) for a, b in zip(bounds, bounds[1:], strict=False)]
