"""Measures the embedding distance (same metric as pgvector <=>) between
labeled sentence pairs, to choose SEMANTIC_CACHE_SIMILARITY_THRESHOLD.
Does not touch the database.

Usage: python -m scripts.measure_cache_threshold
"""

from collections.abc import Callable

import numpy as np
from app.config.settings import settings
from app.nlp.embedding_model import EmbeddingModel
from app.nlp.gloss_analyzer import GlossAnalyzer
from app.nlp.text_normalizer import normalize

# (cached sentence, incoming sentence)
SHOULD_HIT = [
    ("¿Cuál es su nombre?", "¿Cómo se llama usted?"),
    ("¿Cuál es su nombre?", "¿Cuál es tu nombre?"),
    ("¿Cuál es su nombre?", "cual es su nombre"),
    ("Hola, ¿cómo estás?", "Hola, ¿cómo está?"),
    ("Hola, ¿cómo estás?", "hola como estas"),
    ("Me llamo Julián.", "Me llamo Julian"),
    ("Mi nombre es Julián.", "Me llamo Julián."),
    ("Tengo 20 años.", "tengo 20 años"),
    ("Firme aquí, por favor.", "Por favor, firme aquí."),
    ("Espere un momento, por favor.", "Espere un momento."),
    ("No traiga copias adicionales.", "No traiga copias extra."),
    ("¿Dónde vive?", "¿Dónde vive usted?"),
]

SHOULD_MISS = [
    ("Hola, ¿cómo estás?", "¿cómo estás?"),
    ("¿Cuál es su número de documento?", "¿Cuál es su nombre?"),
    ("Hola, tengo una pregunta.", "Tengo una pregunta."),
    ("Mi nombre es Julian, tengo 20 años.", "Mi nombre es Julián."),
    ("Mi nombre es Julian, tengo 20 años.", "Tengo 20 años."),
    ("Me llamo Julián.", "Me llamo Andrea."),
    ("Mi nombre es Julián.", "Mi nombre es Carlos."),
    ("Tengo 20 años.", "Tengo 35 años."),
    ("Su cita quedó confirmada para las tres de la tarde.", "Su cita quedó confirmada para las cinco de la tarde."),
    ("Vivo en Bogotá.", "Vivo en Medellín."),
    ("Firme aquí, por favor.", "Firme allá, por favor."),
    ("¿Dónde vive?", "¿Dónde trabaja?"),
]


def cosine_distance(a: list[float], b: list[float]) -> float:
    a, b = np.asarray(a), np.asarray(b)
    return float(1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def measure(
    model: EmbeddingModel, analyzer: GlossAnalyzer, pairs: list[tuple[str, str]], prepare: Callable[[str], str]
) -> list[float]:
    distances = []
    for cached, incoming in pairs:
        same_type = analyzer.analyze(cached).category == analyzer.analyze(incoming).category
        distance = cosine_distance(model.embed(prepare(cached)), model.embed(prepare(incoming)))
        distances.append(distance)
        note = "" if same_type else "  (otro tipo de frase: el caché nunca los compara)"
        print(f"  {distance:.3f}  {cached!r} <- {incoming!r}{note}")
    return distances


def report(model: EmbeddingModel, analyzer: GlossAnalyzer, title: str, prepare: Callable[[str], str]) -> None:
    print(f"===== {title}")
    print("Deberían ACERTAR:")
    hit = measure(model, analyzer, SHOULD_HIT, prepare)
    print("\nDeberían FALLAR:")
    miss = measure(model, analyzer, SHOULD_MISS, prepare)

    threshold = settings.semantic_cache_similarity_threshold
    print(f"\nUmbral {threshold}:")
    print(f"  aciertos correctos: {sum(d <= threshold for d in hit)}/{len(hit)}")
    print(f"  aciertos indebidos: {sum(d <= threshold for d in miss)}/{len(miss)}\n")


def main() -> None:
    model = EmbeddingModel()
    analyzer = GlossAnalyzer()
    report(model, analyzer, "Texto original", lambda text: text)
    report(model, analyzer, "Texto normalizado", normalize)


if __name__ == "__main__":
    main()
