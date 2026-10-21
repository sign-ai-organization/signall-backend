import asyncio

from app.config.settings import settings
from app.nlp.llm_client import LLMClient

PRESET_SENTENCES = [
    "¿Cuál es su nombre?",
    "No tengo el documento conmigo.",
    "Firme aquí, por favor.",
    "Todo está listo.",
    "¿Ya diligenció el formulario?",
]


async def run_presets(client: LLMClient) -> None:
    for sentence in PRESET_SENTENCES:
        glosses = await client.transform(sentence)
        print(f"{sentence!r} -> {glosses}")


async def run_interactive(client: LLMClient) -> None:
    print("\nEscriba una oración y presione Enter. Escriba 'salir' para terminar.\n")
    while True:
        sentence = input("Oración > ").strip()
        if not sentence:
            continue
        if sentence.lower() in {"salir", "exit", "quit"}:
            break

        glosses = await client.transform(sentence)
        print(f"  -> {glosses}\n")


async def main() -> None:
    client = LLMClient(
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_temperature,
        settings.llm_timeout_ms,
        settings.llm_max_retries,
    )

    print("1. Correr casos predeterminados")
    print("2. Escribir mis propias oraciones")
    choice = input("Elija una opción (1/2) > ").strip()

    if choice == "1":
        await run_presets(client)
    elif choice == "2":
        await run_interactive(client)
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    asyncio.run(main())
