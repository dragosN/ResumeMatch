"""LLM / embedding provider protocols and factory.

Ollama is the default. To add Claude (or another provider):
1. Implement ChatProvider / EmbeddingProvider in e.g. llm/claude.py
2. Register the name in get_chat_provider / get_embedding_provider
3. Set LLM_PROVIDER=claude (and credentials) in .env

Call sites never import a concrete provider — only these factories.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import get_settings


@runtime_checkable
class ChatProvider(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        """Return a JSON-serializable dict conforming to `schema` (JSON Schema)."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


def get_chat_provider() -> ChatProvider:
    settings = get_settings()
    name = settings.llm_provider.lower().strip()
    if name == "ollama":
        from app.llm.ollama import OllamaChatProvider

        return OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
        )
    if name in {"claude", "anthropic", "openai", "azure"}:
        raise NotImplementedError(
            f"Provider '{name}' is reserved but not implemented yet. "
            "Use LLM_PROVIDER=ollama, or add an adapter under app/llm/."
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {name}")


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    name = settings.embedding_provider.lower().strip()
    if name == "ollama":
        from app.llm.ollama import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embed_model,
        )
    if name in {"claude", "anthropic", "openai", "azure"}:
        raise NotImplementedError(
            f"Embedding provider '{name}' is reserved but not implemented yet. "
            "Use EMBEDDING_PROVIDER=ollama, or add an adapter under app/llm/."
        )
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {name}")
