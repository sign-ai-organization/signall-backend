import re
import unicodedata

from app.domain.models import PhraseType
from app.nlp.models import Fingerprint

INTERROGATIVE_WORDS = {
    "que", "cual", "cuales", "como", "donde", "cuando",
    "quien", "quienes", "cuanto", "cuanta", "cuantos", "cuantas",
    "por que", "para que",
}

# The same words spelled the way they are written when they ask a question.
# The accent is what separates them from the relative pronoun in a declaration
# ("cuando termine…"), and it is what makes a question without "?" detectable.
_ACCENTED_INTERROGATIVE_WORDS = {
    "qué", "cuál", "cuáles", "cómo", "dónde", "cuándo",
    "quién", "quiénes", "cuánto", "cuánta", "cuántos", "cuántas",
    "por qué", "para qué",
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


def _starts_with_interrogative_word(original_text: str) -> bool:
    """True when the sentence opens with an accented question word.

    This is the signal that replaces the missing "?". Measured on the 100
    sentences of CO-02 without punctuation (2026-11-05):

    - requiring the interrogative word *anywhere* fixes the 20 content
      questions but breaks 11 other sentences, because "que", "como", "donde"
      and "cuando" are also relative pronouns in affirmatives ("la dirección
      coincide con la que tenemos registrada", "cuando termine el trámite le
      avisaremos");
    - requiring it *at the start* but ignoring the accent fixes the same 20 and
      breaks 3 ("cuando termine…", "quien firmó…", "donde vive usted no
      afecta…");
    - requiring it at the start **with the accent** fixes all 20 content
      questions and breaks none: in Spanish the interrogative pronoun carries
      the accent ("cuál", "dónde", "qué") and the relative one does not. It is
      the same word, and the accent is what the language uses to tell them
      apart.

    The cost is that a transcript that arrives without accents keeps the old
    behaviour instead of guessing. That is the safe side of the trade: an
    unaccented "cuando" at the start of a declaration must stay affirmative.
    A declaration whose subject is an interrogative clause ("Cómo se llama el
    sistema no es relevante") still reads as a question; it is one of the edge
    cases the fixture already marks as difficult, and telling it apart needs a
    parser, not a word list.
    """
    words = re.findall(r"[a-záéíóúüñ]+", original_text.lower())
    if not words:
        return False
    if words[0] in _ACCENTED_INTERROGATIVE_WORDS:
        return True
    return len(words) >= 2 and f"{words[0]} {words[1]}" in _ACCENTED_INTERROGATIVE_WORDS


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
        # A content question without "?" is still a content question: Whisper
        # often delivers the transcript with no punctuation. The question word
        # at the start is the lexical signal; the mark is only a confirmation.
        # YES_NO_QUESTION has no lexical marker at all in Spanish (it depends on
        # intonation), so it still needs the "?" and without it stays as a
        # documented limitation.
        if has_interrogative_word and (has_question_mark or _starts_with_interrogative_word(text)):
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
