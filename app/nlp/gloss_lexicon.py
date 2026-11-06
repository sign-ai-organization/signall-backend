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
   is added; first person adds YO the same way. A sentence that uses the
   third-person-singular verb form shared by "usted" and "él/ella" (e.g.
   "¿Se siente mal?" — "siente" is also how "usted" conjugates) is
   genuinely ambiguous between the two, and defaults to TU: the system
   talks directly to the person rather than guessing a third party.
   A sentence with no person marker at all (no pronoun, no conjugated verb)
   is left untouched — there is nothing to attach a pronoun to.

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
_FIRST_PERSON_WORDS = {
    "yo", "mi", "mis",
    "estoy", "tengo", "siento", "vivo", "quiero", "necesito",
    "puedo", "voy", "soy", "como", "trabajo", "hablo", "vengo",
}
# Third-person-singular present forms, which "usted" also uses ("¿usted
# siente...?" and "¿él siente...?" conjugate the same way). Their presence
# with no explicit pronoun is the ambiguous case decision 2 resolves: talk
# directly to the person instead of guessing a third party.
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
    elif words & _AMBIGUOUS_VERB_WORDS:
        # "¿Se siente mal?": ambiguous between usted and él/ella. Talk
        # directly to the person instead of assuming a third party (owner
        # decision), rather than defaulting on sentences with no person
        # marker at all.
        pronoun = "TU"
    else:
        return glosses

    display = vocabulary.get(normalize_gloss(pronoun), pronoun)
    return [display, *glosses]
