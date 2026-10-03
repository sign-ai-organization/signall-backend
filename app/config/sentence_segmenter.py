from typing import Literal

from pydantic import BaseModel, Field

# Word lists are compared against normalized text: lowercase, no accents.


class SentenceSegmenterSettings(BaseModel):
    enabled: bool = True
    spacy_model: str = "es_core_news_md"

    # --- Post-processing ---
    post_processing_enabled: bool = True
    # A fragment with fewer words than this is merged into a neighbor (1 = never).
    min_fragment_words: int = Field(default=1, ge=1)
    short_fragment_merge_direction: Literal["previous", "next"] = "previous"
    # What to do with a fragment made only of filler words.
    filler_policy: Literal["merge", "discard"] = "merge"
    fillers: list[str] = Field(default_factory=lambda: [
        "asi que bueno", "y bueno", "asi que", "o sea", "entonces", "bueno",
        "pues", "este", "eh", "y si", "y",
    ])

    # --- Shared by the marker and clause rules ---
    # Minimum words that must remain on EACH side of a cut.
    min_words_per_side: int = Field(default=3, ge=1)
    interrogative_words: list[str] = Field(default_factory=lambda: [
        "que", "cual", "cuales", "como", "donde", "cuando",
        "quien", "quienes", "cuanto", "cuanta", "cuantos", "cuantas",
    ])
    # Interrogatives that only count when written with an accent in the original text.
    ambiguous_interrogatives_without_accent: list[str] = Field(default_factory=lambda: [
        "que", "como", "donde", "cuando", "quien", "quienes",
    ])
    # Words right before an interrogative that make it an indirect question (no cut).
    indirect_question_introducers: list[str] = Field(default_factory=lambda: [
        "se", "saber", "sabe", "digame", "dime", "diga", "pregunto", "preguntaron",
        "pregunta", "explique", "mire", "ver", "depende", "importa", "entiendo",
        "entendi", "recuerdo", "acuerdo", "es", "era", "que", "ni",
    ])
    # Words that stay attached to the interrogative after them: the cut goes before them.
    question_prefixes: list[str] = Field(default_factory=lambda: [
        "en", "de", "por", "para", "con", "a", "y", "o",
    ])
    # An interrogative right after an infinitive is treated as an indirect question.
    infinitive_introduces_indirect: bool = True

    # --- Punctuation rules ---
    # Cut before an opening ¿ or ¡ in the middle of a sentence.
    cut_before_opening_mark: bool = True
    # Abbreviations whose period does not end a sentence (without the period).
    abbreviations: list[str] = Field(default_factory=lambda: [
        "sr", "sra", "srta", "dr", "dra", "no", "nro", "num", "cra", "cr", "cl",
        "cll", "av", "apto", "apt", "tel", "cel", "etc", "ud", "uds", "cc", "ti",
    ])
    # Abbreviations only when followed by a number ("No. 12-34").
    numeric_abbreviations: list[str] = Field(default_factory=lambda: ["no", "nro", "num"])

    # --- Discourse marker rules ---
    cut_markers: list[str] = Field(default_factory=lambda: ["asi que bueno", "y bueno", "o sea"])
    cut_before_interrogative: bool = True
    cut_after_closing: bool = True
    # Expressions that close a unit: a cut may go right after them.
    unit_closings: list[str] = Field(default_factory=lambda: [
        "por favor", "gracias", "muchas gracias", "buenos dias", "buenas tardes",
        "buenas noches", "muy bien", "listo", "perdon", "que pena con usted", "de una",
    ])
    # No cut after a closing when the next word is one of these.
    no_cut_after_closing_before: list[str] = Field(default_factory=lambda: ["y", "o", "e", "u"])
    # Closings count only at the start of a fragment, except these.
    closings_anywhere: list[str] = Field(default_factory=lambda: ["por favor"])

    # --- Clause rules (spaCy) ---
    # Words that make the clause right after them subordinate.
    subordinators: list[str] = Field(default_factory=lambda: [
        "que", "si", "cuando", "como", "porque", "donde", "aunque", "mientras",
    ])
    # Subordinators that open a new sentence when they follow a complete one.
    sentence_opening_subordinators: list[str] = Field(default_factory=lambda: [
        "si", "cuando", "aunque", "mientras",
    ])
    # Conjunctions right before a verb that keep the same sentence.
    non_cutting_coordinators: list[str] = Field(default_factory=lambda: [
        "pero", "y", "o", "ni", "e", "u",
    ])
    # Words added to the start of a new clause, walking left from its verb.
    clause_start_words: list[str] = Field(default_factory=lambda: [
        "no", "nunca", "tampoco", "ya", "solo", "tambien", "ahora", "despues",
        "primero", "luego", "entonces",
        "este", "esta", "esto", "ese", "esa", "eso", "estos", "estas", "esos", "esas",
        "yo", "tu", "el", "ella", "usted", "nosotros", "ellos", "ellas", "ustedes",
        "me", "te", "se", "le", "lo", "la", "les", "los", "las", "nos",
    ])
    # How many words to the left are searched for the start of a nominal subject.
    max_subject_words: int = 3

    # --- Hybrid chain ---
    # After the punctuation split, a fragment with at least this many words is
    # re-processed as unpunctuated text.
    reprocess_min_words: int = 8
