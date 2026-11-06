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
   grammatically second person and the glosses do not already have TU, one
   is added; first person adds YO the same way. A sentence whose subject is
   hidden by a reflexive verb (e.g. "¿Se siente mal?" — "siente" is also how
   "usted" conjugates) is genuinely ambiguous between "usted" and "él/ella",
   and defaults to TU: the system talks directly to the person rather than
   guessing a third party. A sentence with no person marker at all (no
   pronoun, no conjugated verb) is left untouched.

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


def _inflection_candidates(normalized: str) -> list[str]:
    """Every singular/gender/Ñ variant of a normalized gloss, minus itself."""
    variants = {normalized}

    if normalized.endswith("S") and len(normalized) > 1:
        variants.add(normalized[:-1])

    for variant in list(variants):
        if variant.endswith("A"):
            variants.add(variant[:-1] + "O")
        elif variant.endswith("O"):
            variants.add(variant[:-1] + "A")

    # The dataset spells Ñ correctly ("NIÑO") but the model or the STT may
    # produce the bare "N" ("NINO"/"NINOS"). Try swapping each "N" in turn
    # rather than guessing which one, since a word can have several.
    for variant in list(variants):
        for index, char in enumerate(variant):
            if char == "N":
                variants.add(variant[:index] + "Ñ" + variant[index + 1 :])

    variants.discard(normalized)
    return list(variants)


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

    Does nothing when the glosses already carry a pronoun or there is
    nothing to attach one to.
    """
    if not glosses:
        return glosses

    folded = {normalize_gloss(gloss) for gloss in glosses}
    if "TU" in folded or "YO" in folded:
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
    return [display, *glosses]
