"""Provider abstraction for deterministic and live prompt execution."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from .prompts import PROMPT_REGISTRY, validate_prompt_output


class ProviderError(RuntimeError):
    pass


class ModelProvider(ABC):
    def __init__(self, model: str, temperature: float = 0.0, token_limit: int = 1800) -> None:
        if temperature < 0 or temperature > 2:
            raise ValueError("temperature must be between 0 and 2")
        if token_limit < 64:
            raise ValueError("token_limit must be at least 64")
        self.model = model
        self.temperature = temperature
        self.token_limit = token_limit
        self.executions: list[dict[str, Any]] = []

    def _record(self, stage: str, prompt_version: str) -> None:
        self.executions.append({
            "stage": stage,
            "model": self.model,
            "prompt_version": prompt_version,
            "temperature": self.temperature,
            "token_limit": self.token_limit,
            "executed_at": datetime.now(UTC).isoformat(),
        })

    @abstractmethod
    def specialist_call(self, prompt: str, model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def second_pass_call(self, prompt: str = "second_pass", model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "temperature": self.temperature,
            "token_limit": self.token_limit,
            "executions": list(self.executions),
        }


class LocalDeterministicProvider(ModelProvider):
    """Records local execution while the pipeline uses its deterministic adapters."""

    def __init__(self) -> None:
        super().__init__(model="local-deterministic", temperature=0.0, token_limit=0x400)

    def specialist_call(self, prompt: str, model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        stage = prompt if prompt in PROMPT_REGISTRY else next((name for name, spec in PROMPT_REGISTRY.items() if spec["system_instruction"] == prompt), "")
        if stage not in {"revenue", "cash_flow", "related_party", "language"}:
            raise ProviderError("Unknown specialist prompt")
        self._record(stage, PROMPT_REGISTRY[stage]["version"])
        supplied = (payload or {}).get("deterministic_output", {"findings": []})
        return validate_prompt_output(stage, supplied)

    def second_pass_call(self, prompt: str = "second_pass", model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if prompt not in {"second_pass", PROMPT_REGISTRY["second_pass"]["system_instruction"]}:
            raise ProviderError("Unknown second-pass prompt")
        self._record("second_pass", PROMPT_REGISTRY["second_pass"]["version"])
        supplied = (payload or {}).get("deterministic_output", {"explained": [], "unresolved": []})
        return validate_prompt_output("second_pass", supplied)


class LiveLLMProvider(ModelProvider):
    """OpenAI-compatible JSON provider; secrets remain in server-side environment variables."""

    def __init__(
        self,
        model: str = "gpt-5-mini",
        temperature: float = 0.0,
        token_limit: int = 1800,
        endpoint: str | None = None,
        api_key: str | None = None,
    ) -> None:
        super().__init__(model, temperature, token_limit)
        self.endpoint = endpoint or os.getenv("FINTRACE_LLM_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        self.api_key = api_key or os.getenv("FINTRACE_LLM_API_KEY", "")
        self.retry_events: list[dict[str, Any]] = []

    def metadata(self) -> dict[str, Any]:
        metadata = super().metadata()
        metadata["retry_events"] = list(self.retry_events)
        return metadata

    def _execute(self, stage: str, payload: dict[str, Any], model: str | None, temperature: float | None) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("FINTRACE_LLM_API_KEY is required for live execution")
        spec = PROMPT_REGISTRY[stage]
        selected_model = model or self.model
        selected_temperature = self.temperature if temperature is None else temperature
        body = json.dumps({
            "model": selected_model,
            "temperature": selected_temperature,
            "max_tokens": self.token_limit,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": spec["system_instruction"]},
                {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
            ],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "FinTrace/0.2",
            },
            method="POST",
        )
        for attempt in range(6):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                content = raw["choices"][0]["message"]["content"]
                output = json.loads(content)
                break
            except urllib.error.HTTPError as error:
                try:
                    detail = error.read().decode("utf-8", errors="replace")
                    parsed = json.loads(detail)
                    detail = str(parsed.get("error", {}).get("message", detail))
                except (OSError, TypeError, json.JSONDecodeError):
                    detail = error.reason or "no response detail"
                retry_match = re.search(r"try again in\s+([0-9.]+)(ms|s)", detail, flags=re.IGNORECASE)
                if error.code == 429 and retry_match and attempt < 5:
                    parsed_delay = float(retry_match.group(1)) / 1000 if retry_match.group(2).casefold() == "ms" else float(retry_match.group(1))
                    delay = min(parsed_delay + 1.0, 60.0)
                    self.retry_events.append({
                        "stage": stage,
                        "attempt": attempt + 1,
                        "http_status": 429,
                        "delay_seconds": round(delay, 3),
                        "recorded_at": datetime.now(UTC).isoformat(),
                    })
                    time.sleep(delay)
                    continue
                raise ProviderError(f"Live model execution failed with HTTP {error.code}: {detail[:500]}") from error
            except (OSError, KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
                raise ProviderError(f"Live model execution failed: {error}") from error
        self.executions.append({
            "stage": stage,
            "model": selected_model,
            "prompt_version": spec["version"],
            "temperature": selected_temperature,
            "token_limit": self.token_limit,
            "executed_at": datetime.now(UTC).isoformat(),
        })
        return validate_prompt_output(stage, output)

    def specialist_call(self, prompt: str, model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        stage = prompt if prompt in PROMPT_REGISTRY else next((name for name, spec in PROMPT_REGISTRY.items() if spec["system_instruction"] == prompt), "")
        if stage not in {"revenue", "cash_flow", "related_party", "language"}:
            raise ProviderError(f"Unsupported specialist stage: {stage}")
        return self._execute(stage, payload or {}, model, temperature)

    def second_pass_call(self, prompt: str = "second_pass", model: str | None = None, temperature: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if prompt not in {"second_pass", PROMPT_REGISTRY["second_pass"]["system_instruction"]}:
            raise ProviderError("Unknown second-pass prompt")
        return self._execute("second_pass", payload or {}, model, temperature)
