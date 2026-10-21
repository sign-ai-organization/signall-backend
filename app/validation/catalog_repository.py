import asyncpg

from app.domain.models import CatalogEntry

# Accented vowels -> unaccented, on purpose an explicit table instead of
# `unicodedata.normalize("NFD", ...)`: that decomposition splits the tilde off
# Ñ, so stripping the combining marks would turn NIÑO into NINO, which is a
# different gloss and would resolve to the wrong sign.
_ACCENTS = str.maketrans({"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U"})

# The glossing prompt asks for uppercase with no punctuation, but the dataset
# spells its question words ¿QUÉ? / ¿CUÁNDO? / ¿CÓMO?. The catalog stores the
# bare word, so the same marks are dropped on both sides of the lookup.
_PUNCTUATION = str.maketrans("", "", "¿?")


def normalize_gloss(gloss: str) -> str:
    """Folds a gloss to the single key both sides of a lookup agree on.

    Case, accents, the inverted-question marks the dataset uses, and stray
    whitespace all collapse; Ñ survives untouched. Returns "" for input that is
    only whitespace or punctuation, so it can never collide with a real entry.
    """
    folded = gloss.strip().upper().translate(_ACCENTS).translate(_PUNCTUATION)
    return " ".join(folded.split())


class CatalogRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self.cache: dict[str, CatalogEntry] = {}

    async def load_all(self) -> None:
        # Ordered so the catalog's vocabulary is identical on every start. The
        # LLM prompt embeds it, and a stable list keeps the prompt byte-stable
        # (any server-side prompt cache depends on it).
        rows = await self._pool.fetch(
            "SELECT gloss, glb_animation_path FROM catalog ORDER BY id_sign"
        )

        # Keyed by the folded gloss so an accented emission from the LLM finds
        # the unaccented row. In production `semantic_cache` already holds both
        # "COMO" and "CÓMO" for the same phrase, so this is not hypothetical.
        # `CatalogEntry.gloss` keeps the stored spelling for display.
        self.cache = {
            normalize_gloss(row["gloss"]): CatalogEntry(
                gloss=row["gloss"], glb_path=row["glb_animation_path"]
            )
            for row in rows
        }

    def search(self, gloss: str) -> CatalogEntry | None:
        return self.cache.get(normalize_gloss(gloss))

    def vocabulary(self) -> dict[str, str]:
        """Every catalog gloss as folded key -> display spelling.

        The LLM prompt is built from this so the model can only propose signs
        the app can actually play, and the prompt's post-hoc repair resolves
        against the same keys (`COMO ESTAS` resolves an accented `CÓMO ESTÁS`).
        """
        return {folded: entry.gloss for folded, entry in self.cache.items()}
