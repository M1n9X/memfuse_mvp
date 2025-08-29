import os
from unittest import mock

import responses

from memfuse.config import Settings
from memfuse.embeddings import JinaEmbeddingClient


@responses.activate
def test_jina_embed_success():
    settings = Settings.from_env()
    client = JinaEmbeddingClient(settings)

    responses.add(
        responses.POST,
        "https://api.jina.ai/v1/embeddings",
        json={
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        },
        status=200,
    )

    vecs = client.embed(["hello", "world"])
    assert vecs == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
