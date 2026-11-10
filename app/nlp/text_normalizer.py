import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_MARK_RE = re.compile(r"\s+([.,;:?!])")
_WORD_RE = re.compile(r"[a-z0-9ñ]+")


def clean(text: str) -> str:
    """Collapses whitespace and removes spaces before closing marks; keeps the original text."""
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return _SPACE_BEFORE_MARK_RE.sub(r"\1", text)


def strip_accents(text: str) -> str:
    """Removes accents and diaereses but keeps ñ."""
    text = text.replace("ñ", "\0").replace("Ñ", "\1")
    decomposed = unicodedata.normalize("NFD", text)
    without_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return without_accents.replace("\0", "ñ").replace("\1", "Ñ")


def normalized_words(text: str) -> list[str]:
    """Lowercase words without accents or marks, only for comparisons."""
    return _WORD_RE.findall(strip_accents(text.lower()))


def normalize(text: str) -> str:
    return " ".join(normalized_words(text))


def substitute_synonyms(normalized: str, synonyms: dict[str, str]) -> str:
    """Replaces a normalized phrase's synonyms with their canonical form.

    `synonyms` maps a normalized phrase (as `normalize()` would produce it)
    to its normalized canonical replacement, longest phrase first so "con
    permiso" wins over "con". Used so two sentences that differ only in a
    catalog synonym ("tengo mucha hambre" / "tengo muy hambre") land on the
    same `semantic_cache` key instead of two that happen to mean the same
    sign.
    """
    if not synonyms or not normalized:
        return normalized

    words = normalized.split()
    ordered = sorted(synonyms.items(), key=lambda item: len(item[0].split()), reverse=True)

    out: list[str] = []
    index = 0
    while index < len(words):
        for phrase, canonical in ordered:
            phrase_words = phrase.split()
            end = index + len(phrase_words)
            if words[index:end] == phrase_words:
                out.extend(canonical.split())
                index = end
                break
        else:
            out.append(words[index])
            index += 1
    return " ".join(out)
