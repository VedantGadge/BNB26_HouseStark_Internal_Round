"""Minimal OpenRouter client with strict structured-output handling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator

from app.config import Settings


class ProviderError(Exception):
    def __init__(self, category: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


@dataclass(frozen=True)
class ProviderResult:
    payload: dict[str, Any]
    actual_model: str | None
    provider: str | None
    input_tokens: int | None
    output_tokens: int | None


class StructuredTextProvider(Protocol):
    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, Any],
        routing: dict[str, Any],
    ) -> ProviderResult: ...


class OpenRouterProvider:
    """OpenRouter's OpenAI-compatible chat endpoint, without exposing credentials."""

    def __init__(self, settings: Settings) -> None:
        if settings.openrouter_api_key is None:
            raise ProviderError("configuration", "OpenRouter API key is not configured")
        self._api_key = settings.openrouter_api_key.get_secret_value()
        self._base_url = settings.openrouter_base_url.rstrip("/")

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, Any],
        routing: dict[str, Any],
    ) -> ProviderResult:
        models = [routing["default_model"], *routing.get("fallback_models", [])]
        if routing.get("free_only") and any(not model.endswith(":free") for model in models):
            raise ProviderError("configuration", "Free-only routing requires :free model IDs")

        last_error: ProviderError | None = None
        calls = 0
        repaired = False
        pending = list(models)
        while pending and calls < routing["max_calls"]:
            model = pending.pop(0)
            calls += 1
            try:
                result = self._request_model(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema_name=schema_name,
                    schema=schema,
                    timeout_seconds=routing["timeout_seconds"],
                    max_output_tokens=routing["max_output_tokens"],
                    require_structured_output=routing["require_structured_output"],
                    reasoning_effort=routing.get("reasoning_effort", "minimal"),
                )
                invalid = next(Draft202012Validator(schema).iter_errors(result.payload), None)
                if invalid is not None:
                    raise ProviderError("invalid_response", "Model output did not match the schema")
                return result
            except ProviderError as error:
                last_error = error
                if (
                    error.category == "invalid_response"
                    and not repaired
                    and calls < routing["max_calls"]
                ):
                    repaired = True
                    pending.insert(0, model)
                    user_prompt += (
                        "\nYour previous response was invalid. Return one JSON object matching "
                        "the schema exactly, with no commentary and only supplied identifiers."
                    )
                elif not error.retryable or not pending:
                    raise
        raise last_error or ProviderError("unavailable", "No configured model was attempted", True)

    def _request_model(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, Any],
        timeout_seconds: float,
        max_output_tokens: int,
        require_structured_output: bool,
        reasoning_effort: str = "minimal",
    ) -> ProviderResult:
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_output_tokens,
            "reasoning": {"effort": reasoning_effort, "exclude": True},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        if require_structured_output:
            payload["provider"] = {"require_parameters": True}
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code <= 599
            category = "rate_limited" if error.code == 429 else "provider_error"
            raise ProviderError(
                category,
                f"OpenRouter request failed ({error.code})",
                retryable,
            ) from error
        except (TimeoutError, URLError) as error:
            raise ProviderError("unavailable", "OpenRouter is unavailable", True) from error
        except json.JSONDecodeError as error:
            raise ProviderError("invalid_response", "OpenRouter returned invalid JSON") from error

        if (body.get("choices") or [{}])[0].get("finish_reason") == "length":
            raise ProviderError(
                "output_limit",
                "The model exhausted its output budget. Increase OPENROUTER_MAX_OUTPUT_TOKENS "
                "or configure a fallback model with a smaller reasoning budget.",
                retryable=True,
            )
        try:
            content = body["choices"][0]["message"]["content"]
            output = json.loads(content) if isinstance(content, str) else content
            if not isinstance(output, dict):
                raise TypeError("structured response must be an object")
        except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise ProviderError(
                "invalid_response",
                "OpenRouter returned malformed structured output",
            ) from error
        usage = body.get("usage") or {}
        return ProviderResult(
            payload=output,
            actual_model=body.get("model"),
            provider=(body.get("provider") or None),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
