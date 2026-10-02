from spacy.language import Language
from spacy.tokens import Token

from app.config.sentence_segmenter import SentenceSegmenterSettings
from app.nlp.segmenter._discourse_markers import is_infinitive, is_interrogative
from app.nlp.segmenter._normalizer import normalize


def _is_finite_verb(token: Token) -> bool:
    return token.pos_ in ("VERB", "AUX") and "Fin" in token.morph.get("VerbForm")


def split_by_clauses(text: str, nlp: Language, config: SentenceSegmenterSettings) -> list[str]:
    """Cuts before each finite verb that starts a new independent clause.

    Only POS tags and morphology are used, not the dependency tree.
    """
    doc = nlp(text)
    words = [t for t in doc if not (t.is_punct or t.is_space)]
    normalized = [normalize(t.text) for t in words]

    def interrogative(j: int) -> bool:
        return is_interrogative(words[j].text, normalized[j], config)

    cuts: list[int] = []
    last_cut = 0
    has_verb = False           # a finite verb was already seen in the current fragment
    subordinate = False        # the first clause of the fragment is subordinate
    que_since_verb = False     # an unaccented "que" appeared since the last verb
    indirect = False           # the fragment had an indirect question

    for i, token in enumerate(words):
        if normalized[i] == "que" and token.text.lower() == "que":
            que_since_verb = True
        if not _is_finite_verb(token):
            continue

        # 1. Where this verb's clause starts.
        j = i
        starts_with_question = False
        while j - 1 > last_cut and (normalized[j - 1] in config.clause_start_words or interrogative(j - 1)):
            j -= 1
            starts_with_question |= interrogative(j)
        if starts_with_question and j - 1 > last_cut and normalized[j - 1] in config.question_prefixes:
            j -= 1        # "|| y dónde vive", "|| en qué le ayudo"

        subject_with_y = False
        if not starts_with_question:
            # Nominal subject before the verb: walk left and take the first valid start.
            k = j
            while (k - 1 > last_cut and j - k < config.max_subject_words
                   and (words[k - 1].pos_ in ("DET", "NOUN", "PROPN", "ADJ")
                        or interrogative(k - 1))):
                k -= 1
                if interrogative(k):                            # "|| cuántos años tiene"
                    j, starts_with_question = k, True
                    if j - 1 > last_cut and normalized[j - 1] in config.question_prefixes:
                        j -= 1
                    break
                if k - 1 > last_cut and normalized[k - 1] == "y":   # "|| y mi teléfono es"
                    j, subject_with_y = k - 1, True
                    break
                # "|| mi apellido es". Possessives only, and not after a verb, pronoun
                # or preposition: there it is an object ("revisar el sistema").
                if ("Yes" in words[k].morph.get("Poss")
                        and words[k - 1].pos_ not in ("ADP", "DET", "VERB", "AUX", "PRON")):
                    j = k
                    break

        previous = normalized[j - 1] if j > 0 else ""

        # A subordinate clause opening a new sentence: cut before the subordinator.
        opens_subordinate = has_verb and previous in config.sentence_opening_subordinators
        if opens_subordinate:
            j -= 1
            previous = normalized[j - 1] if j > 0 else ""

        # 2. Whether to cut here.
        if not has_verb:
            subordinate = previous in config.subordinators
            has_verb = True
            que_since_verb = False
            continue

        cut = True
        if subordinate:
            cut = False                 # this is the main clause of the subordinate one
            subordinate = False
        elif opens_subordinate:
            subordinate = True          # its main clause stays attached to it
        elif not subject_with_y and previous in config.subordinators + config.non_cutting_coordinators:
            cut = False
        elif j > 0 and words[j - 1].pos_ == "ADP":
            cut = False                 # "desde hace cinco años"
        elif que_since_verb:
            cut = False
        elif starts_with_question and (
                previous in config.indirect_question_introducers
                or (config.infinitive_introduces_indirect and is_infinitive(previous))):
            cut = False
            indirect = True
        elif starts_with_question and indirect and previous in ("y", "o"):
            cut = False
        elif normalized[j] in ("y", "o") and indirect:
            cut = False

        left = sum(1 for x in normalized[last_cut:j] if x)
        right = sum(1 for x in normalized[j:] if x)
        if cut and (left < config.min_words_per_side or right < config.min_words_per_side):
            cut = False

        if cut:
            cuts.append(j)
            last_cut = j
            indirect = False
        que_since_verb = False

    # Cut the original text at the character offset of each cut word.
    bounds = [0] + [words[c].idx for c in cuts] + [len(text)]
    return [text[a:b].strip() for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()]
