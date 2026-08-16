"""Ollama chat + embedding adapters."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse JSON from model output, tolerating markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:400]!r}")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Model JSON root is not an object")
    return data


class OllamaChatProvider:
    def __init__(self, base_url: str, model: str, timeout: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        """Ask Ollama for JSON. Prefer format=json; fall back to fenced JSON parse."""
        schema_hint = json.dumps(schema, indent=2)
        system_full = (
            f"{system}\n\n"
            "Respond with a single JSON object only — no markdown, no commentary.\n"
            f"The JSON must conform to this schema:\n{schema_hint}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_full},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            body = resp.json()
        content = body.get("message", {}).get("content", "")
        if not content:
            raise ValueError(f"Empty Ollama chat response: {body!r}")
        return _extract_json_object(content)


class OllamaEmbeddingProvider:
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        with httpx.Client(timeout=self.timeout) as client:
            for text in texts:
                resp = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                resp.raise_for_status()
                body = resp.json()
                embedding = body.get("embedding")
                if not embedding:
                    raise ValueError(f"Empty Ollama embedding response: {body!r}")
                vectors.append(embedding)
        return vectors
