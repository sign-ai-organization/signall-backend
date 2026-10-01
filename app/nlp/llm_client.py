from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = (
    "You translate short Spanish sentences into LSC (Lengua de Señas "
    "Colombiana) glosses, following these general sign-language glossing "
    "conventions:\n"
    "- Topic-comment order: the topic of the sentence goes first.\n"
    "- Drop articles (el, la, los, las, un, una) and the copula (ser/estar) "
    "when the meaning stays clear without them.\n"
    "- Use the base/infinitive form of verbs, never conjugated.\n"
    "- For content questions (qué, cómo, dónde, cuándo, quién, cuánto), "
    "place the question word at the end.\n"
    "- Place negation (no, nunca, tampoco) at the end of the sentence.\n"
    "\n"
    "A gloss is a single word representing one sign: UPPERCASE, no accent "
    "marks (á->A, é->E, í->I, ó->O, ú->U — keep Ñ as is), no punctuation. "
    "Respond with ONLY the glosses, separated by commas, nothing else — "
    "no explanation, no sentence-type classification, no separator other "
    "than a comma.\n"
    "\n"
    "Examples:\n"
    "Input: ¿Cuál es su nombre?\n"
    "Output: NOMBRE,TU,QUE\n"
    "Input: No tengo el documento conmigo.\n"
    "Output: YO,DOCUMENTO,TENER,NO\n"
    "Input: Firme aquí, por favor.\n"
    "Output: FAVOR,AQUI,FIRMAR"
)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        timeout_ms: int,
        base_url: str = "",
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout_ms = timeout_ms
        # An empty base_url means the provider default (OpenAI). Pointing it at
        # any OpenAI-compatible endpoint runs the same prompt on a local model
        # instead: Ollama, LM Studio, vLLM, llama.cpp's server.
        self._chat = ChatOpenAI(
            api_key=api_key,
            base_url=base_url or None,
            model=model,
            temperature=temperature,
            timeout=timeout_ms / 1000,
        )

    def transform(self, text: str) -> list[str]:
        response = self._chat.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", text),
            ]
        )
        return self._parse_glosses(response.content)

    def _parse_glosses(self, content: str) -> list[str]:
        separator = "," if "," in content else None
        return [gloss.strip().upper() for gloss in content.split(separator) if gloss.strip()]
