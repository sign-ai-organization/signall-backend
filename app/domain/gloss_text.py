"""Canonical spelling of a gloss, shared by the two components that need it.

The catalog (validation) and the glosado (NLP) have to agree on how a gloss
is written before they compare it: the catalog stores the bare word and the
model answers in uppercase with punctuation. The rule that folds both sides to
the same key used to live in `app.validation.catalog_repository`, and the NLP
imported it from there. That import jumped the interface between two
components (PR-TRA-01): the NLP reached into the internals of the validation
component for a pure function.

The rule belongs to the domain, which both components already depend on, so
it lives here. It has no state: it only folds a string.
"""

# Accented vowels -> unaccented, on purpose an explicit table instead of
# `unicodedata.normalize("NFD", ...)`: that decomposition splits the tilde off
# Ñ, so stripping the combining marks would turn NIÑO into NINO, which is a
# different gloss and would resolve to the wrong sign.
_ACCENTS = str.maketrans({"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U"})

# The glossing prompt asks for uppercase with no punctuation, but the dataset
# spells its question words ¿QUÉ? / ¿CUÁNDO? / ¿CÓMO?. The catalog stores the
# bare word, so the same marks are dropped on both sides of the lookup.
#
# The sentence marks are dropped for a different reason (2026-11-05): a model
# that ends its answer with a period ("HOLA, BUENOS DIAS.") used to produce a
# gloss "BUENOS DIAS." that did not exist in the catalog, so the sign came out
# as unavailable. Punctuation never distinguishes two glosses of this dataset,
# and dropping it on both sides is what makes the lookup agree.
_PUNCTUATION = str.maketrans("", "", "¿?.,;:!¡…")


def normalize_gloss(gloss: str) -> str:
    """Folds a gloss to the single key both sides of a lookup agree on.

    Case, accents, the inverted-question marks the dataset uses, and stray
    whitespace all collapse; Ñ survives untouched. Returns "" for input that is
    only whitespace or punctuation, so it can never collide with a real entry.
    """
    folded = gloss.strip().upper().translate(_ACCENTS).translate(_PUNCTUATION)
    return " ".join(folded.split())
