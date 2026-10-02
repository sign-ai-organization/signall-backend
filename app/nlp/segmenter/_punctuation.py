from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.text_normalizer import normalize

CLOSING_MARKS = (".", "?", "!", "…")
OPENING_MARKS = ("¿", "¡")
# Characters that may follow a closing mark: 'end.)' or 'end."'
_WRAPPERS = "\"')]»”’"


def _ends_sentence(token: str, next_token: str | None, config: SentenceSegmenterSettings) -> bool:
    stripped = token.rstrip(_WRAPPERS)
    if not stripped.endswith(CLOSING_MARKS):
        return False
    if stripped.endswith(("?", "!", "…", "...")):
        return True

    base = normalize(stripped[:-1])
    if base in config.numeric_abbreviations:
        return not (next_token and next_token[0].isdigit())
    if base in config.abbreviations:
        return False
    if len(base) == 1 and base.isalpha():
        # "a. m." only ends a sentence if the next word is capitalized.
        return next_token is None or next_token[0].isupper()
    return True


def split_by_punctuation(text: str, config: SentenceSegmenterSettings) -> list[str]:
    tokens = text.split()
    fragments: list[str] = []
    current: list[str] = []

    for i, token in enumerate(tokens):
        if config.cut_before_opening_mark and token.startswith(OPENING_MARKS) and current:
            fragments.append(" ".join(current))
            current = []
        current.append(token)
        next_token = tokens[i + 1] if i + 1 < len(tokens) else None
        if _ends_sentence(token, next_token, config):
            fragments.append(" ".join(current))
            current = []

    if current:
        fragments.append(" ".join(current))
    return fragments
