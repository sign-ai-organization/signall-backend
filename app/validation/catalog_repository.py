import logging

import asyncpg
from app.domain.models import CatalogEntry
from app.persistence.database import RetryPolicy, run_with_retry

logger = logging.getLogger(__name__)

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


class CatalogRepository:
    def __init__(self, pool: asyncpg.Pool | None, retry_policy: RetryPolicy | None = None) -> None:
        # None means the database was unreachable at start-up. The catalog stays
        # empty and every sign comes out as unavailable; the service still runs.
        self._pool = pool
        self._retry_policy = retry_policy or RetryPolicy()
        self.cache: dict[str, CatalogEntry] = {}
        # Display spelling pairs (synonym, canonical gloss), for callers that
        # normalize on their own terms (`SemanticCache` folds whole sentences,
        # not single glosses, so it cannot reuse `normalize_gloss` keys here).
        self.synonym_pairs: list[tuple[str, str]] = []

    async def load_all(self) -> None:
        """Load the catalog into memory.

        Ordered so the catalog is identical on every start.
        """
        pool = self._pool
        if pool is None:
            logger.warning("No database pool: the catalog stays empty")
            return

        rows = await run_with_retry(
            lambda: pool.fetch(
                "SELECT gloss, semantic_category, glb_animation_path FROM catalog ORDER BY id_sign"
            ),
            self._retry_policy,
            "could not load the catalog",
        )

        # Keyed by the folded gloss so an accented emission from the LLM finds
        # the unaccented row. In production `semantic_cache` already holds both
        # "COMO" and "CÓMO" for the same phrase, so this is not hypothetical.
        # `CatalogEntry.gloss` keeps the stored spelling for display.
        self.cache = {
            normalize_gloss(row["gloss"]): CatalogEntry(
                gloss=row["gloss"],
                semantic_category=row["semantic_category"] or "",
                glb_path=row["glb_animation_path"],
            )
            for row in rows
        }

        await self._load_synonyms(pool)

    async def _load_synonyms(self, pool: asyncpg.Pool) -> None:
        """Folds `catalog_synonym` into the same vocabulary the glosses use.

        A synonym is wired to the *same* `CatalogEntry` its canonical gloss
        already has, so `vocabulary()` resolves it automatically and
        `LLMClient._repair_glosses` needs no change for this rule (Fase 2,
        decisión 4). The table may not exist yet on an older database; that
        is not an error, it just means no synonym to load.
        """
        try:
            rows = await run_with_retry(
                lambda: pool.fetch(
                    """
                    SELECT cs.synonym, c.gloss
                    FROM catalog_synonym cs
                    JOIN catalog c ON c.id_sign = cs.id_sign
                    """
                ),
                self._retry_policy,
                "could not load catalog synonyms",
            )
        except asyncpg.UndefinedTableError:
            logger.info("catalog_synonym does not exist yet; no synonyms loaded")
            return

        self.synonym_pairs = []
        for row in rows:
            canonical_key = normalize_gloss(row["gloss"])
            canonical_entry = self.cache.get(canonical_key)
            if canonical_entry is None:
                logger.warning(
                    "Synonym %r points to gloss %r, which is not in the catalog", row["synonym"], row["gloss"]
                )
                continue

            synonym_key = normalize_gloss(row["synonym"])
            if synonym_key in self.cache:
                logger.warning(
                    "Synonym %r collides with an existing catalog gloss; keeping the catalog entry",
                    row["synonym"],
                )
                continue

            self.cache[synonym_key] = canonical_entry
            self.synonym_pairs.append((row["synonym"], row["gloss"]))

    def search(self, gloss: str) -> CatalogEntry | None:
        return self.cache.get(normalize_gloss(gloss))

    def vocabulary(self) -> dict[str, str]:
        """Every catalog gloss as folded key -> display spelling.

        The post-hoc repair of the model's answer resolves against these keys
        (`COMO ESTAS` resolves an accented `CÓMO ESTÁS`). The list does not go
        into the prompt: decision D-7 (owner, 2026-10-16) took it out of it.
        """
        return {folded: entry.gloss for folded, entry in self.cache.items()}

    def categories(self) -> dict[str, str]:
        """The same folded keys, mapped to the catalog's semantic category.

        `LLMClient` uses it to place the verb where the corpus places it, which
        needs to tell a verb from a noun; the display spelling alone cannot.
        Synonyms inherit the category of the gloss they point to, because they
        are the same `CatalogEntry`.
        """
        return {folded: entry.semantic_category for folded, entry in self.cache.items()}
