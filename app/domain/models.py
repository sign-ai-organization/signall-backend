from enum import Enum

from pydantic import BaseModel


class PhraseType(str, Enum):
    AFFIRMATIVE = "AFFIRMATIVE"
    YES_NO_QUESTION = "YES_NO_QUESTION"
    CONTENT_QUESTION = "CONTENT_QUESTION"
    NEGATIVE = "NEGATIVE"
    IMPERATIVE = "IMPERATIVE"


class Segment(BaseModel):
    type: PhraseType
    glosses: list[str]


class CatalogEntry(BaseModel):
    gloss: str
    glb_path: str
    # The category the corpus gives to this sign. It travels with the gloss so
    # the client has the same grouping the catalog has.
    semantic_category: str = ""


class Gloss(BaseModel):
    text: str
    available: bool
    glb_path: str = ""
    semantic_category: str = ""


class ValidatedSegment(BaseModel):
    type: PhraseType
    glosses: list[Gloss]
