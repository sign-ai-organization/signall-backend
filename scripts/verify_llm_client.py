from app.config.settings import settings
from app.nlp.llm_client import LLMClient

PRESET_SENTENCES = [
    "¿Cuál es su nombre?",
    "No tengo el documento conmigo.",
    "Firme aquí, por favor.",
    "Todo está listo.",
    "¿Ya diligenció el formulario?",
]


def run_presets(client: LLMClient) -> None:
    for sentence in PRESET_SENTENCES:
        glosses = client.transform(sentence)
        print(f"{sentence!r} -> {glosses}")


def run_interactive(client: LLMClient) -> None:
    print("\nEscriba una oración y presione Enter. Escriba 'salir' para terminar.\n")
    while True:
        sentence = input("Oración > ").strip()
        if not sentence:
            continue
        if sentence.lower() in {"salir", "exit", "quit"}:
            break

        glosses = client.transform(sentence)
        print(f"  -> {glosses}\n")


def main() -> None:
    client = LLMClient(
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_temperature,
        settings.llm_timeout_ms,
    )

    print("1. Correr casos predeterminados")
    print("2. Escribir mis propias oraciones")
    choice = input("Elija una opción (1/2) > ").strip()

    if choice == "1":
        run_presets(client)
    elif choice == "2":
        run_interactive(client)
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    main()
