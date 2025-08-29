from __future__ import annotations

import os
from typing import Iterable, List

import requests

from .config import Settings


class JinaEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.jina_api_key or os.getenv("JINA_API_KEY", "")
        self.model = settings.embedding_model
        self.url = "https://api.jina.ai/v1/embeddings"

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        inputs = list(texts)
        if not inputs:
            return []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = {
            "model": self.model,
            "task": "text-matching",
            "input": inputs,
        }
        resp = requests.post(self.url, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        embeddings: List[List[float]] = [
            item["embedding"] for item in payload.get("data", [])
        ]
        return embeddings
