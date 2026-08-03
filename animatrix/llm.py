from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

import anthropic

from animatrix.config import settings

FENCE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


class LLMError(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class LLM:
    """Cienka warstwa nad Anthropic SDK. Cała komunikacja z modelem idzie tędy,
    żeby księgowanie tokenów i obsługa błędów były w jednym miejscu."""

    def __init__(self, on_usage: Callable[[int, int], None] | None = None):
        cfg = settings()
        if not cfg.has_anthropic:
            raise LLMError(
                "Brak ANTHROPIC_API_KEY. Skopiuj .env.example do .env i uzupełnij klucz."
            )
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self.model = cfg.anthropic_model
        self.effort = cfg.anthropic_effort
        self._on_usage = on_usage

    def _account(self, response: Any) -> None:
        if self._on_usage is None:
            return
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        self._on_usage(getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0)

    def _output_config(self, schema: dict | None) -> dict:
        cfg: dict[str, Any] = {"effort": self.effort}
        if schema is not None:
            cfg["format"] = {"type": "json_schema", "schema": schema}
        return cfg

    def json_call(
        self,
        system: str,
        user: str,
        schema: dict,
        *,
        max_tokens: int = 16000,
    ) -> dict:
        """Wymusza odpowiedź zgodną ze schematem JSON (structured outputs)."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config=self._output_config(schema),
            )
        except anthropic.APIStatusError as exc:  # 4xx/5xx z treścią
            raise LLMError(f"Anthropic API {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Brak połączenia z Anthropic API: {exc}") from exc

        self._account(response)

        if response.stop_reason == "refusal":
            raise LLMError("Model odmówił odpowiedzi na ten prompt.")
        if response.stop_reason == "max_tokens":
            raise LLMError("Odpowiedź modelu została ucięta (max_tokens). Skróć zakres i spróbuj ponownie.")

        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        if not text.strip():
            raise LLMError("Model zwrócił pustą odpowiedź.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Odpowiedź modelu nie jest poprawnym JSON-em: {exc}") from exc

    def text_call(self, system: str, user: str, *, max_tokens: int = 32000) -> str:
        """Długa odpowiedź tekstowa (kod scen). Strumieniowo, żeby nie wpaść w timeout HTTP."""
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort},
            ) as stream:
                response = stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError(f"Brak połączenia z Anthropic API: {exc}") from exc

        self._account(response)

        if response.stop_reason == "refusal":
            raise LLMError("Model odmówił odpowiedzi na ten prompt.")

        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        if not text.strip():
            raise LLMError("Model zwrócił pustą odpowiedź.")
        return text

    def code_call(self, system: str, user: str, *, max_tokens: int = 32000) -> str:
        return extract_code(self.text_call(system, user, max_tokens=max_tokens))


def extract_code(text: str) -> str:
    """Wyciąga kod z bloku ```python. Jeśli modelowi zdarzy się odpowiedzieć samym
    kodem bez fence'a, zwracamy tekst jak jest."""
    matches = FENCE_RE.findall(text)
    if matches:
        return max(matches, key=len).strip() + "\n"
    stripped = text.strip()
    if stripped.startswith("from ") or stripped.startswith("import "):
        return stripped + "\n"
    raise LLMError("W odpowiedzi modelu nie ma bloku kodu ```python.")
