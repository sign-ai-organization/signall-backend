import re
import unicodedata

from app.domain.models import PhraseType
from app.nlp.models import Fingerprint

INTERROGATIVE_WORDS = {
    "que", "cual", "cuales", "como", "donde", "cuando",
    "quien", "quienes", "cuanto", "cuanta", "cuantos", "cuantas",
    "por que", "para que",
}

NEGATION_PARTICLES = {
    "no", "nunca", "jamas", "tampoco", "ni",
}

# Closed list of frequent imperative verbs for this project's domain
# ("Registro de Datos Basicos", 50-sign corpus, ADR-002). Not a real
# morphological analyzer: a closed-list heuristic scoped on purpose.
IMPERATIVE_VERBS = {
    "espere", "firme", "escriba", "entregue", "presente",
    "acerquese", "siga", "pase", "tome", "complete",
    "indique", "confirme", "verifique", "deje", "muestre",
    "repita", "digame", "digale", "llene", "diligencie",
}

INITIAL_FILLERS = {"por favor", "porfavor", "por-favor"}


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _has_question_mark(original_text: str) -> bool:
    return "?" in original_text


def _tokenize(normalized_text: str) -> list[str]:
    return re.findall(r"[a-z]+", normalized_text)


def _has_interrogative_word(normalized_text: str) -> bool:
    words = _tokenize(normalized_text)
    joined_words = " ".join(words)
    for pattern in INTERROGATIVE_WORDS:
        if " " in pattern:
            if pattern in joined_words:
                return True
        elif pattern in words:
            return True
    return False


def _has_negation(normalized_text: str) -> bool:
    words = _tokenize(normalized_text)
    return any(word in NEGATION_PARTICLES for word in words)


def _has_imperative(normalized_text: str) -> bool:
    words = _tokenize(normalized_text)
    if not words:
        return False

    if len(words) >= 2 and f"{words[0]} {words[1]}" in INITIAL_FILLERS:
        words = words[2:]
    elif words[0] in INITIAL_FILLERS:
        words = words[1:]

    if not words:
        return False

    return words[0] in IMPERATIVE_VERBS


class GlossAnalyzer:
    def analyze(self, text: str) -> Fingerprint:
        normalized_text = _normalize(text)

        has_question_mark = _has_question_mark(text)
        has_interrogative_word = _has_interrogative_word(normalized_text)
        has_negation = _has_negation(normalized_text)
        has_imperative = _has_imperative(normalized_text)

        signals: list[PhraseType] = []
        if has_question_mark and has_interrogative_word:
            signals.append(PhraseType.CONTENT_QUESTION)
        elif has_question_mark:
            signals.append(PhraseType.YES_NO_QUESTION)
        if has_imperative:
            signals.append(PhraseType.IMPERATIVE)
        if has_negation:
            signals.append(PhraseType.NEGATIVE)
        if not signals:
            signals.append(PhraseType.AFFIRMATIVE)

        # Collision priority: interrogative > imperative > negative > affirmative
        if PhraseType.CONTENT_QUESTION in signals:
            category = PhraseType.CONTENT_QUESTION
        elif PhraseType.YES_NO_QUESTION in signals:
            category = PhraseType.YES_NO_QUESTION
        elif PhraseType.IMPERATIVE in signals:
            category = PhraseType.IMPERATIVE
        elif PhraseType.NEGATIVE in signals:
            category = PhraseType.NEGATIVE
        else:
            category = PhraseType.AFFIRMATIVE

        secondary_signals = [signal for signal in signals if signal != category]
        has_collision = len(signals) > 1

        return Fingerprint(
            category=category,
            secondary_signals=secondary_signals,
            has_collision=has_collision,
        )
