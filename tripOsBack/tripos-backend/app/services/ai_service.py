import json
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.core.config import settings


class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key and not self._uses_local_provider():
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI chat is not configured. Set OPENAI_API_KEY or configure "
                    "a local OpenAI-compatible provider on the API server."
                ),
            )

    @staticmethod
    def _uses_local_provider() -> bool:
        hostname = urlsplit(settings.OPENAI_BASE_URL).hostname
        return hostname in {"localhost", "127.0.0.1", "::1"}

    def generate_response(self, messages: list[dict[str, Any]]) -> str:
        headers = (
            {"Authorization": f"Bearer {self.api_key}"}
            if self.api_key
            else {}
        )
        try:
            response = httpx.post(
                f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                headers=headers,
                json={"model": settings.OPENAI_MODEL, "messages": messages},
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            try:
                error_data = error.response.json()
            except json.JSONDecodeError:
                error_data = {}
            provider_message = (
                error_data.get("error", {}).get("message", "")
                if isinstance(error_data, dict)
                and isinstance(error_data.get("error"), dict)
                else ""
            )
            if not isinstance(provider_message, str):
                provider_message = ""
            if status_code == 401:
                explanation = (
                    "Check the API key and OPENAI_BASE_URL for the selected provider."
                )
            elif status_code == 429:
                explanation = "Check the AI provider quota and rate limits."
            else:
                explanation = provider_message[:300]
            raise HTTPException(
                status_code=502,
                detail=(
                    f"AI provider request failed (HTTP {status_code}). "
                    f"{explanation}".strip()
                ),
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to reach the AI provider "
                    f"({type(error).__name__}). Check the API server's network connection."
                ),
            ) from error

        try:
            payload = response.json()
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=502,
                detail="The AI provider returned an invalid response.",
            ) from error

        choices = payload.get("choices", []) if isinstance(payload, dict) else []
        content = (
            choices[0].get("message", {}).get("content")
            if choices and isinstance(choices[0], dict)
            else None
        )
        if not isinstance(content, str) or not content.strip():
            raise HTTPException(
                status_code=502,
                detail="The AI provider returned an empty response.",
            )
        return content.strip()