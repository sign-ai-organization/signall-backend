import re
from pathlib import Path

from app.domain.models import PhraseType
from app.nlp.gloss_analyzer import GlossAnalyzer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "oraciones_prueba.md"

HEADER_TO_PHRASE_TYPE = {
    "AFIRMATIVA": PhraseType.AFFIRMATIVE,
    "INTERROGATIVA_SI_NO": PhraseType.YES_NO_QUESTION,
    "INTERROGATIVA_CONTENIDO": PhraseType.CONTENT_QUESTION,
    "NEGATIVA": PhraseType.NEGATIVE,
    "IMPERATIVA": PhraseType.IMPERATIVE,
}


def load_sentences_by_category() -> dict[PhraseType, list[tuple[str, bool]]]:
    """Returns {category: [(sentence, is_edge_case), ...]}.
    Edge cases are lines ending in "(*)" — sentences the fixture's own
    comments document as expected to fail under the current heuristic.
    """
    sentences_by_category: dict[PhraseType, list[tuple[str, bool]]] = {}
    current_category: PhraseType | None = None

    with open(FIXTURE_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").strip()
            if not line:
                continue

            header_match = re.match(r"^##\s+(\w+)", line)
            if header_match:
                current_category = HEADER_TO_PHRASE_TYPE.get(header_match.group(1))
                if current_category and current_category not in sentences_by_category:
                    sentences_by_category[current_category] = []
                continue

            if line.startswith("#") or current_category is None:
                continue

            line = re.sub(r"^\d+\.\s+", "", line)
            is_edge_case = line.endswith("(*)")
            sentence = re.sub(r"\s*\(\*\)\s*$", "", line).strip()
            if sentence:
                sentences_by_category[current_category].append((sentence, is_edge_case))

    return sentences_by_category


def main() -> None:
    analyzer = GlossAnalyzer()
    sentences_by_category = load_sentences_by_category()

    total_correct = 0
    total_sentences = 0
    edge_case_failures_expected = 0

    for expected_category, sentences in sentences_by_category.items():
        correct = 0
        for sentence, is_edge_case in sentences:
            fingerprint = analyzer.analyze(sentence)
            is_correct = fingerprint.category == expected_category
            if is_correct:
                correct += 1
            elif is_edge_case:
                edge_case_failures_expected += 1

        total = len(sentences)
        print(f"{expected_category.value:20} {correct:>3}/{total:<3} ({correct / total * 100:.1f}%)")
        total_correct += correct
        total_sentences += total

    print("-" * 45)
    print(
        f"{'TOTAL':20} {total_correct:>3}/{total_sentences:<3} "
        f"({total_correct / total_sentences * 100:.1f}%)"
    )
    print(f"(of which, failures on sentences marked (*) as expected: {edge_case_failures_expected})")

    # What Whisper usually delivers: no "?" at all. Only an accented question
    # word at the start is a lexical signal (CO-02, 2026-11-05). The unaccented
    # ones are relative pronouns in these declarations and must stay as they
    # are; that is why they are in this list.
    no_punctuation = [
        ("cuál es su nombre", PhraseType.CONTENT_QUESTION),
        ("dónde vive", PhraseType.CONTENT_QUESTION),
        ("qué documento trajo", PhraseType.CONTENT_QUESTION),
        ("cómo se llama", PhraseType.CONTENT_QUESTION),
        ("por qué necesita este trámite", PhraseType.CONTENT_QUESTION),
        ("para qué necesita el certificado", PhraseType.CONTENT_QUESTION),
        ("la dirección coincide con la que tenemos registrada", PhraseType.AFFIRMATIVE),
        ("cuando termine el trámite le avisaremos por correo", PhraseType.AFFIRMATIVE),
        ("quien firmó el documento aparece en el registro", PhraseType.AFFIRMATIVE),
        ("donde vive usted no afecta el proceso de registro", PhraseType.NEGATIVE),
    ]
    print("\nsin signo de interrogación:")
    for sentence, expected in no_punctuation:
        got = analyzer.analyze(sentence).category
        mark = "ok  " if got == expected else "FAIL"
        print(f"  {mark} {sentence!r} -> {got.value} (esperado {expected.value})")


if __name__ == "__main__":
    main()
