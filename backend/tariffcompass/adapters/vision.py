"""Photo understanding through a cloud vision adapter; a deterministic fake by default (VISION_FAKE=true).

The adapter turns a product photo into short factual sentences ("a cylindrical steel tumbler with a sliding
lid") that join the product description. The fake never invents product facts: it recognises the sample
photos shipped with the demo seed by their SHA-256 and otherwise says only what it can read from the file
itself (format and size), marking every sentence as uncertain.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

SUPPORTED = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG", "image/webp": b"RIFF"}


@dataclass(frozen=True)
class PhotoFacts:
    sentences: tuple[str, ...]
    certain: bool
    adapter: str  # "offline photo reader" or the cloud model id


@runtime_checkable
class VisionAdapter(Protocol):
    def describe(self, image: bytes, mime: str) -> PhotoFacts: ...


def sniff(image: bytes) -> str | None:
    for mime, magic in SUPPORTED.items():
        if image.startswith(magic) and (mime != "image/webp" or image[8:12] == b"WEBP"):
            return mime
    return None


class FakeVision:
    """Known sample photos map to fixed sentences; anything else yields no product facts."""

    def __init__(self, known: dict[str, tuple[str, ...]] | None = None) -> None:
        self.known = known or {}

    def describe(self, image: bytes, mime: str) -> PhotoFacts:
        digest = hashlib.sha256(image).hexdigest()
        if digest in self.known:
            return PhotoFacts(self.known[digest], True, "offline photo reader")
        kind = (sniff(image) or mime).split("/")[-1].upper()
        return PhotoFacts(
            (f"A {kind} photo was attached; no product details could be read from it offline.",),
            False,
            "offline photo reader",
        )
