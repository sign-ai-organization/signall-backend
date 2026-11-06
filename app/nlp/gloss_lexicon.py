"""Resolves glosses the catalog's exact lookup misses, Fase 2 of the plan.

Two rules, both already decided by the owner (ver el plan de implementación,
Fase 2):

1. Inflection (`resolve_inflection`): the model answers with a word that is a
   predictable inflection of a catalog gloss ("NINOS", "BIENVENIDOS") instead
   of the catalog's own form ("NIÑO", "BIENVENIDO"). This tries singular,
   masculine/feminine and the N/Ñ spelling before giving up on the gloss.

2. Implicit pronoun (`insert_implicit_pronoun`): LSC50 keeps the pronoun
   (YO, TU) only when the model said it explicitly, but Spanish drops it
   constantly ("estoy contento" has no "yo"). If the sentence is
   grammatically second person and the glosses do not already carry the
   person, one is added; first person adds YO the same way. Its position is
   after a leading question gloss ("POR QUE,TU,TRISTE") and it is not added
   when the gloss is already a phrasal sign that contains the person
   ("COMO ESTAS"). A sentence whose subject is hidden by a reflexive verb
   (e.g. "¿Se siente mal?") is genuinely ambiguous between "usted" and
   "él/ella", and defaults to TU: the system talks directly to the person
   rather than guessing a third party. A sentence with no person marker at
   all (no pronoun, no conjugated verb) is left untouched.

   Two things this rule must NOT do, learned by measuring the 30 FR-01
   phrases (2026-11-06): "mi"/"mis" are first-person possessives that point
   at somebody else ("mi abuelo nunca trabaja" is not YO), and a third-person
   verb with an explicit subject is not ambiguous ("la mujer es juiciosa" is
   not TU). Only the reflexive "se" makes the subject invisible, so the
   ambiguous case requires it.

Neither rule touches `normalize_gloss` or the catalog/cache key: both work
one layer above it, on the list of glosses `llm_client._repair_glosses`
already produced.
"""

from app.nlp.text_normalizer import normalized_words
from app.validation.catalog_repository import normalize_gloss

# Verb forms and possessives that mark the sentence as addressed to "tú", or
# spoken about "yo". This is not an exhaustive conjugator: it covers the
# forms the test phrases actually use, which is what this layer exists to
# repair.
_SECOND_PERSON_WORDS = {
    "tu", "tus", "usted",
    "estas", "tienes", "sientes", "vives", "quieres", "necesitas",
    "puedes", "vas", "eres", "comes", "trabajas", "hablas", "vienes",
}
# "mi"/"mis" are NOT here on purpose: they are possessives that point at
# somebody else, not at the speaker ("mi abuelo nunca trabaja" is not YO).
_FIRST_PERSON_WORDS = {
    "yo",
    "estoy", "tengo", "siento", "vivo", "quiero", "necesito",
    "puedo", "voy", "soy", "como", "trabajo", "hablo", "vengo",
}
# Third-person-singular present forms, which "usted" also uses ("¿usted
# siente...?" and "¿él siente...?" conjugate the same way). On their own they
# are not ambiguous: "la mujer es juiciosa" has an explicit subject. The
# ambiguity decision 2 resolves needs the reflexive "se" that hides the
# subject ("¿Se siente mal?"), so the rule below also requires it.
_AMBIGUOUS_VERB_WORDS = {
    "esta", "tiene", "siente", "vive", "quiere", "necesita",
    "puede", "va", "es", "come", "trabaja", "habla", "viene",
}
# The gloss that opens a question. The implicit pronoun is inserted after it,
# because in LSC the question sign comes first: "¿Por qué estás triste?" is
# POR QUE,TU,TRISTE.
_QUESTION_OPENERS = {
    "que", "como", "donde", "cuando", "quien", "por que", "cuanto", "cual",
}


def _tilde_variants(word: str) -> list[str]:
    """`word` with each "N" swapped for "Ñ", one at a time.

    The dataset spells Ñ correctly ("NIÑO") but the model or the STT may
    produce the bare "N" ("NINO"/"NINOS"). Trying each "N" in turn is cheaper
    than guessing which one, since a word can have several.
    """
    return [word[:index] + "Ñ" + word[index + 1 :] for index, char in enumerate(word) if char == "N"]


def _gender_flip(word: str) -> str | None:
    """The other gender's ending, when the word has one."""
    if word.endswith("A"):
        return word[:-1] + "O"
    if word.endswith("O"):
        return word[:-1] + "A"
    return None


def _inflection_candidates(normalized: str) -> list[str]:
    """Every singular/gender/Ñ variant of a normalized gloss, in a fixed order.

    The order **is** the rule, not an implementation detail. The catalog has
    both NIÑO and NIÑA, so for "NIÑAS" the candidates NIÑA and NIÑO are both
    valid lookups and only one of them is right. This used to return a `set`,
    which made the answer depend on `PYTHONHASHSEED`: the same phrase came out
    NIÑO in one container and NIÑA in the next, and that is why two
    consecutive runs of the 30 FR-01 phrases disagreed on phrases 006 and 027
    (measured 2026-11-06).

    Minimal edit first: drop the plural, then fix the Ñ, and only then flip the
    gender. "NIÑAS" reaches NIÑA before NIÑO, and "NINOS" reaches NIÑO before
    NIÑA, which is the gender the sentence itself used.
    """
    singular = normalized[:-1] if normalized.endswith("S") and len(normalized) > 1 else normalized

    ordered: list[str] = []
    for base in (singular, _gender_flip(singular)):
        if base is None:
            continue
        for candidate in (base, *_tilde_variants(base)):
            if candidate != normalized and candidate not in ordered:
                ordered.append(candidate)
    return ordered



def resolve_inflection(gloss: str, vocabulary: dict[str, str]) -> str | None:
    """The catalog's display spelling for an inflected form of `gloss`, if any."""
    normalized = normalize_gloss(gloss)
    for candidate in _inflection_candidates(normalized):
        entry = vocabulary.get(candidate)
        if entry is not None:
            return entry
    return None


def insert_implicit_pronoun(text: str, glosses: list[str], vocabulary: dict[str, str]) -> list[str]:
    """Adds TU or YO to `glosses` when the sentence implies one but omits it.

    Does nothing when the glosses already carry the person, or there is nothing
    to attach one to.

    Two things about *where* and *whether* it lands, learned by measuring the 30
    FR-01 phrases (2026-11-06):

    - In a question the question gloss goes first, so the pronoun is inserted
      after it: "¿Por qué estás triste?" is POR QUE,TU,TRISTE, not
      TU,POR QUE,TRISTE.
    - A phrasal gloss that already contains the person does not get a second
      one: "¿Cómo estás?" is the single gloss COMO ESTAS, and adding TU in
      front of it says the person twice.
    """
    if not glosses:
        return glosses

    folded = {normalize_gloss(gloss) for gloss in glosses}
    if "TU" in folded or "YO" in folded:
        return glosses
    if any(_carries_person(gloss) for gloss in glosses):
        return glosses

    words = set(normalized_words(text))
    if words & _SECOND_PERSON_WORDS:
        pronoun = "TU"
    elif words & _FIRST_PERSON_WORDS:
        pronoun = "YO"
    elif words & _AMBIGUOUS_VERB_WORDS and "se" in words:
        # "¿Se siente mal?": the reflexive hides the subject, so it is
        # ambiguous between usted and él/ella. Talk directly to the person
        # instead of assuming a third party (owner decision). Without the
        # "se" the subject is explicit and there is nothing ambiguous:
        # "la mujer es juiciosa" is not addressed to the listener.
        pronoun = "TU"
    else:
        return glosses

    display = vocabulary.get(normalize_gloss(pronoun), pronoun)
    position = 1 if normalize_gloss(glosses[0]).lower() in _QUESTION_OPENERS else 0
    return [*glosses[:position], display, *glosses[position:]]


def _carries_person(gloss: str) -> bool:
    """Whether a gloss already says who acts.

    Only *phrasal* glosses are checked. A single word that happens to be on one
    of the person lists — "TRABAJO" is the noun as well as "I work" — would
    suppress a pronoun the sentence really does imply; a phrase like
    "COMO ESTAS" only exists because the person is part of the sign.
    """
    words = normalize_gloss(gloss).lower().split()
    if len(words) < 2:
        return False
    return bool(set(words) & (_SECOND_PERSON_WORDS | _FIRST_PERSON_WORDS))
