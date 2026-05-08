from __future__ import annotations

import hashlib
import math
import re

DIMENSIONS = 16
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

SYNONYMS = {
    "anc": "noise",
    "battery": "charge",
    "clean": "cleaning",
    "cleaner": "cleaning",
    "charging": "charge",
    "return": "returns",
    "usb": "usb-c",
    "waterproof": "rain",
}


def embed_text(text: str, dimensions: int = DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        bucket = stable_bucket(token, dimensions)
        sign = -1.0 if stable_bucket(f"{token}:sign", 2) == 0 else 1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_PATTERN.findall(text.lower().replace("usb-c", "usbc"))
    expanded = []
    for token in tokens:
        normalized = "usb-c" if token == "usbc" else token
        expanded.append(normalized)
        synonym = SYNONYMS.get(normalized)
        if synonym:
            expanded.append(synonym)
    return expanded


def stable_bucket(token: str, dimensions: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % dimensions
