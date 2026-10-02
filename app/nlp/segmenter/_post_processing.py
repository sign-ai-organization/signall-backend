from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.text_normalizer import clean, normalized_words


def _is_only_filler(fragment: str, config: SentenceSegmenterSettings) -> bool:
    words = normalized_words(fragment)
    if not words:
        return True
    fillers = sorted((f.split() for f in config.fillers), key=len, reverse=True)
    i = 0
    while i < len(words):
        for filler in fillers:
            if words[i:i + len(filler)] == filler:
                i += len(filler)
                break
        else:
            return False
    return True


def _join(a: str, b: str) -> str:
    return clean(f"{a} {b}")


def _resolve_fillers(fragments: list[str], config: SentenceSegmenterSettings) -> list[str]:
    if config.filler_policy == "discard":
        return [f for f in fragments if not _is_only_filler(f, config)]

    # "merge": a filler is attached to the start of the next fragment with
    # content, because in speech it usually introduces what follows.
    result: list[str] = []
    pending = ""
    for fragment in fragments:
        if _is_only_filler(fragment, config):
            pending = _join(pending, fragment)
            continue
        result.append(_join(pending, fragment) if pending else fragment)
        pending = ""
    if pending:
        # Trailing fillers go to the last fragment; an all-filler text stays as one fragment.
        if result:
            result[-1] = _join(result[-1], pending)
        else:
            result.append(pending)
    return result


def _merge_short(fragments: list[str], config: SentenceSegmenterSettings) -> list[str]:
    minimum = config.min_fragment_words
    if minimum <= 1:
        return fragments

    def is_short(fragment: str) -> bool:
        return len(normalized_words(fragment)) < minimum

    if config.short_fragment_merge_direction == "previous":
        result: list[str] = []
        for fragment in fragments:
            if is_short(fragment) and result:
                result[-1] = _join(result[-1], fragment)
            else:
                result.append(fragment)
        # A short first fragment has no previous one: it goes to the next.
        if len(result) > 1 and is_short(result[0]):
            result[1] = _join(result[0], result[1])
            result.pop(0)
        return result

    result = []
    for fragment in reversed(fragments):
        if is_short(fragment) and result:
            result[-1] = _join(fragment, result[-1])
        else:
            result.append(fragment)
    result.reverse()
    if len(result) > 1 and is_short(result[-1]):
        result[-2] = _join(result[-2], result[-1])
        result.pop()
    return result


def post_process(fragments: list[str], config: SentenceSegmenterSettings) -> list[str]:
    fragments = [clean(f) for f in fragments]
    fragments = [f for f in fragments if f]
    if not config.post_processing_enabled:
        return fragments
    fragments = _resolve_fillers(fragments, config)
    return _merge_short(fragments, config)
