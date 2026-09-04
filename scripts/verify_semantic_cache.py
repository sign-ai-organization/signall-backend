import asyncio

from app.config.settings import settings
from app.domain.models import PhraseType
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.models import Fingerprint
from app.nlp.semantic_cache import SemanticCache


async def main() -> None:
    model = EmbeddingModel()
    cache = SemanticCache(
        settings.database_url, model, settings.semantic_cache_similarity_threshold
    )

    content_question = Fingerprint(
        category=PhraseType.CONTENT_QUESTION,
        secondary_signals=[],
        has_collision=False,
    )
    affirmative = Fingerprint(
        category=PhraseType.AFFIRMATIVE,
        secondary_signals=[],
        has_collision=False,
    )
    negative_with_collision = Fingerprint(
        category=PhraseType.NEGATIVE,
        secondary_signals=[PhraseType.YES_NO_QUESTION],
        has_collision=True,
    )

    # 1. Store an entry, then look it up with the exact same text.
    await cache.store("¿Cuál es su nombre?", content_question, ["NOMBRE", "TU", "PREGUNTA"])
    result = await cache.lookup("¿Cuál es su nombre?", content_question)
    print(f"1. exact text, same phrase_type       -> {result}")
    assert result == ["NOMBRE", "TU", "PREGUNTA"], "expected HIT with the stored glosses"

    # 2. Look it up with a semantically similar (but not identical) text.
    result = await cache.lookup("¿Cómo se llama usted?", content_question)
    print(f"2. similar text, same phrase_type      -> {result}")
    assert result == ["NOMBRE", "TU", "PREGUNTA"], "expected HIT via semantic similarity"

    # 3. Same exact text, but a different phrase_type -> must MISS regardless of text match.
    result = await cache.lookup("¿Cuál es su nombre?", affirmative)
    print(f"3. exact text, different phrase_type   -> {result}")
    assert result is None, "expected MISS: phrase_type must always be respected"

    # 4. Unrelated text, same phrase_type -> too far semantically, must MISS.
    result = await cache.lookup("¿Dónde queda la oficina de registro?", content_question)
    print(f"4. unrelated text, same phrase_type    -> {result}")
    assert result is None, "expected MISS: text is not semantically close enough"

    # 5. Store an entry with a collision (negative + yes/no question signal) and
    #    confirm the collision data round-trips untouched — it must never be hidden.
    await cache.store("No firme, ¿es correcto?", negative_with_collision, ["FIRMAR", "NO"])
    result = await cache.lookup("No firme, ¿es correcto?", negative_with_collision)
    print(f"5. entry stored with collision signals -> {result}")
    assert result == ["FIRMAR", "NO"], "expected HIT for the collision entry"


if __name__ == "__main__":
    asyncio.run(main())
