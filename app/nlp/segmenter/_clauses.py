from dataclasses import dataclass, field

from spacy.language import Language
from spacy.tokens import Token

from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.segmenter._discourse_markers import is_infinitive, is_interrogative
from app.nlp.text_normalizer import normalize

_SUBJECT_POS = ("DET", "NOUN", "PROPN", "ADJ")
_OBJECT_POS = ("ADP", "DET", "VERB", "AUX", "PRON")


def _is_finite_verb(token: Token) -> bool:
    return token.pos_ in ("VERB", "AUX") and "Fin" in token.morph.get("VerbForm")


def _interrogative_at(words: list[Token], normalized: list[str], index: int,
                      config: SentenceSegmenterSettings) -> bool:
    return is_interrogative(words[index].text, normalized[index], config)


def _starts_clause(words: list[Token], normalized: list[str], index: int,
                   config: SentenceSegmenterSettings) -> bool:
    """Whether the word before the verb belongs to the clause that the verb opens."""
    return normalized[index] in config.clause_start_words or _interrogative_at(words, normalized, index, config)


def _previous_word(normalized: list[str], position: int) -> str:
    return normalized[position - 1] if position > 0 else ""


@dataclass
class _Clause:
    """Where a verb's clause starts and what kind of start it is."""

    position: int
    starts_with_question: bool = False
    subject_with_y: bool = False


@dataclass
class _FragmentState:
    """What is known about the fragment being built while the words are walked.

    A fragment is the text since the last cut. The flags travel with it because
    each verb can only be judged against what the previous verbs left.
    """

    last_cut: int = 0
    has_verb: bool = False
    subordinate: bool = False
    que_since_verb: bool = False
    indirect: bool = False
    cuts: list[int] = field(default_factory=list)


def _question_start(words: list[Token], normalized: list[str], verb: int, last_cut: int,
                    config: SentenceSegmenterSettings) -> _Clause:
    """Walk left from the verb over the words that open an interrogative clause."""
    clause = _Clause(position=verb)
    while clause.position - 1 > last_cut and _starts_clause(words, normalized, clause.position - 1, config):
        clause.position -= 1
        clause.starts_with_question |= _interrogative_at(words, normalized, clause.position, config)
    if (clause.starts_with_question and clause.position - 1 > last_cut
            and normalized[clause.position - 1] in config.question_prefixes):
        clause.position -= 1        # "|| y dónde vive", "|| en qué le ayudo"
    return clause


def _extend_subject(words: list[Token], normalized: list[str], start: int, last_cut: int,
                    config: SentenceSegmenterSettings) -> _Clause | None:
    """The clause start that this candidate word adds, or None when it adds nothing."""
    if _interrogative_at(words, normalized, start, config):
        clause = _Clause(position=start, starts_with_question=True)
        if clause.position - 1 > last_cut and normalized[clause.position - 1] in config.question_prefixes:
            clause.position -= 1
        return clause                                       # "|| cuántos años tiene"

    if start - 1 > last_cut and normalized[start - 1] == "y":
        return _Clause(position=start - 1, subject_with_y=True)    # "|| y mi teléfono es"

    # "|| mi apellido es". Possessives only, and not after a verb, pronoun or
    # preposition: there it is an object ("revisar el sistema").
    if "Yes" in words[start].morph.get("Poss") and words[start - 1].pos_ not in _OBJECT_POS:
        return _Clause(position=start)
    return None


def _subject_start(words: list[Token], normalized: list[str], verb: int, last_cut: int,
                   config: SentenceSegmenterSettings) -> _Clause:
    """Walk left from the verb over the nominal subject that precedes it.

    The walk looks for a subject that is worth starting the clause at —an
    interrogative, a possessive, a "y" in front of one— and the clause start
    only moves when one is found.
    """
    position = verb
    while (position - 1 > last_cut and verb - position < config.max_subject_words
           and (words[position - 1].pos_ in _SUBJECT_POS
                or _interrogative_at(words, normalized, position - 1, config))):
        position -= 1
        clause = _extend_subject(words, normalized, position, last_cut, config)
        if clause is not None:
            return clause
    return _Clause(position=verb)


def _clause_start(words: list[Token], normalized: list[str], verb: int, last_cut: int,
                  config: SentenceSegmenterSettings) -> _Clause:
    """Where the clause of this verb starts, and how it starts."""
    clause = _question_start(words, normalized, verb, last_cut, config)
    if clause.starts_with_question:
        return clause
    return _subject_start(words, normalized, clause.position, last_cut, config)


def _opens_indirect_question(previous: str, config: SentenceSegmenterSettings) -> bool:
    """An interrogative right after these words is an indirect question: no cut."""
    return previous in config.indirect_question_introducers or (
        config.infinitive_introduces_indirect and is_infinitive(previous))


def _continues_indirect_question(word: str, clause: _Clause, previous: str, state: _FragmentState) -> bool:
    """The fragment already had an indirect question and this clause belongs to it."""
    if not state.indirect:
        return False
    if clause.starts_with_question and previous in ("y", "o"):
        return True
    return word in ("y", "o")


def _blocks_cut(words: list[Token], normalized: list[str], clause: _Clause, previous: str,
                state: _FragmentState, config: SentenceSegmenterSettings) -> bool:
    """Whether the clause stays attached to the one being closed."""
    if not clause.subject_with_y and previous in config.subordinators + config.non_cutting_coordinators:
        return True
    if clause.position > 0 and words[clause.position - 1].pos_ == "ADP":
        return True                                     # "desde hace cinco años"
    if state.que_since_verb:
        return True
    if clause.starts_with_question and _opens_indirect_question(previous, config):
        state.indirect = True
        return True
    return _continues_indirect_question(normalized[clause.position], clause, previous, state)


def _has_words_on_both_sides(normalized: list[str], last_cut: int, position: int,
                             config: SentenceSegmenterSettings) -> bool:
    left = sum(1 for x in normalized[last_cut:position] if x)
    right = sum(1 for x in normalized[position:] if x)
    return left >= config.min_words_per_side and right >= config.min_words_per_side


def _decide_cut(words: list[Token], normalized: list[str], clause: _Clause, previous: str,
                opens_subordinate: bool, state: _FragmentState,
                config: SentenceSegmenterSettings) -> bool:
    """Whether this verb opens a new sentence, updating what the fragment now is.

    The first clause of a fragment has no verb of its own to cut against, so the
    state it leaves —subordinate or not— decides the next verb. A subordinate
    clause that opens a sentence keeps its main clause attached to it.
    """
    if state.subordinate:
        state.subordinate = False       # this is the main clause of the subordinate one
        return False
    if opens_subordinate:
        state.subordinate = True
        return True
    return not _blocks_cut(words, normalized, clause, previous, state, config)


def split_by_clauses(text: str, nlp: Language, config: SentenceSegmenterSettings) -> list[str]:
    """Cuts before each finite verb that starts a new independent clause.

    Only POS tags and morphology are used, not the dependency tree.
    """
    doc = nlp(text)
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    normalized = [normalize(t.text) for t in words]
    state = _FragmentState()

    for i, token in enumerate(words):
        _process_word(words, normalized, i, token, state, config)

    # Cut the original text at the character offset of each cut word.
    bounds = [0] + [words[c].idx for c in state.cuts] + [len(text)]
    return [text[a:b].strip() for a, b in zip(bounds, bounds[1:], strict=False) if text[a:b].strip()]


def _is_unaccented_que(token: Token, normalized: str) -> bool:
    return normalized == "que" and token.text.lower() == "que"


def _process_word(words: list[Token], normalized: list[str], index: int, token: Token,
                  state: _FragmentState, config: SentenceSegmenterSettings) -> None:
    """Decides, for one word, whether a new sentence starts at its verb."""
    if _is_unaccented_que(token, normalized[index]):
        state.que_since_verb = True
    if not _is_finite_verb(token):
        return

    clause = _clause_start(words, normalized, index, state.last_cut, config)
    previous = _previous_word(normalized, clause.position)

    # A subordinate clause opening a new sentence: cut before the subordinator.
    opens_subordinate = state.has_verb and previous in config.sentence_opening_subordinators
    if opens_subordinate:
        clause.position -= 1
        previous = _previous_word(normalized, clause.position)

    if not state.has_verb:
        state.subordinate = previous in config.subordinators
        state.has_verb = True
        state.que_since_verb = False
        return

    cut = _decide_cut(words, normalized, clause, previous, opens_subordinate, state, config)
    if cut and _has_words_on_both_sides(normalized, state.last_cut, clause.position, config):
        state.cuts.append(clause.position)
        state.last_cut = clause.position
        state.indirect = False
    state.que_since_verb = False
