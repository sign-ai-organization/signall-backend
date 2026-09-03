from pydantic import BaseModel

from app.domain.models import PhraseType


class Fingerprint(BaseModel):
    category: PhraseType
    secondary_signals: list[PhraseType]
    has_collision: bool
