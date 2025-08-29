from __future__ import annotations

import hashlib


def compute_content_hash(text: str) -> str:
    """Return a stable SHA256 hex digest for the given text.

    Minimal normalization: strip leading/trailing whitespace to avoid trivial
    differences generating distinct hashes.
    """
    normalized = text.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()
