"""Sample evidence files the seed attaches: spec sheets and a supplier email (PDF), and product photos (PNG).

All are generated, byte for byte the same on every run, and labelled as sample documents. The offline photo
reader recognises the sample photos by their SHA-256 (`photo_facts()`), so a photo upload in the demo reads
the same sentences every time; any other photo yields no product facts.
"""

from __future__ import annotations

import hashlib
import io
import struct
import zlib
from functools import cache

SPEC_SHEETS: dict[str, tuple[str, list[str]]] = {
    "NB-KT-0412": (
        "Spec sheet v3",
        [
            "Product: 20 oz tumbler, model TC-20 (sample document)",
            "Capacity: 591 ml (20 US fl oz)",
            "Body: double-wall 18/8 stainless steel, insulated",
            "Lid: sliding lid, BPA-free polypropylene",
            "Finish: powder-coated outer wall",
            "Country of origin: China",
        ],
    ),
    "NB-KT-0388": (
        "Spec sheet v2",
        [
            "Product: 20 oz camp tumbler, model CT-20 (sample document)",
            "Capacity: 591 ml",
            "Body: double-wall stainless steel, air-insulated; the space between the walls is not evacuated",
            "Lid: sliding lid",
            "Country of origin: China",
        ],
    ),
    "NB-KT-0611": (
        "Spec sheet",
        [
            "Product: tri-ply cookware set, 10 pieces (sample document)",
            "Construction: 18/10 stainless steel inner and outer layers, aluminium core",
            "Steel content: 4.1 kg per set; aluminium content: 0.9 kg per set",
            "Country of origin: Germany (melted and poured in Germany)",
        ],
    ),
}

SUPPLIER_EMAILS: dict[str, tuple[str, list[str]]] = {
    "NB-KT-0412": (
        "Supplier email 14 Jan",
        [
            "From: export desk, the supplier (sample document)",
            "Date: 14 January 2026",
            "Re: TC-20 tumbler construction",
            "Confirming that the TC-20 is vacuum-sealed: the air between the inner and outer walls is removed before",
            "the walls are welded shut. The vacuum is what keeps drinks cold for 24 hours.",
        ],
    ),
}

PHOTOS: dict[str, tuple[str, ...]] = {
    "NB-KT-0412": (
        "A cylindrical stainless steel tumbler with a powder-coated outer wall.",
        "A clear sliding lid on top.",
    ),
    "NB-EL-0215": (
        "A bicycle headlight with a rubber strap mount.",
        "The lamp head is shown detached from the mount, held in a hand.",
    ),
}


def _pdf(title: str, lines: list[str]) -> bytes:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER, invariant=1)
    c.setTitle(title)
    c.setAuthor("Sample document")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 720, title)
    c.setFont("Helvetica", 10)
    y = 690
    for line in lines:
        c.drawString(72, y, line)
        y -= 16
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(72, 72, "Sample document generated for the Tariff Compass demo.")
    c.showPage()
    c.save()
    return buf.getvalue()


@cache
def spec_sheet(sku: str) -> tuple[str, bytes]:
    label, lines = SPEC_SHEETS[sku]
    return label, _pdf(f"{label}: {sku}", lines)


@cache
def supplier_email(sku: str) -> tuple[str, bytes]:
    label, lines = SUPPLIER_EMAILS[sku]
    return label, _pdf(label, lines)


def _png(seed: str, w: int = 48, h: int = 48) -> bytes:
    """A small deterministic PNG (a soft gradient keyed by the SKU)."""
    digest = hashlib.sha256(seed.encode()).digest()
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        for x in range(w):
            rows += bytes(((digest[0] + x * 3) % 256, (digest[1] + y * 3) % 256, digest[2]))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )


@cache
def photo(sku: str) -> bytes:
    return _png(f"tariff-compass-sample-photo:{sku}")


@cache
def photo_facts() -> dict[str, tuple[str, ...]]:
    """sha256 of each sample photo → what the offline photo reader says about it."""
    return {hashlib.sha256(photo(sku)).hexdigest(): facts for sku, facts in PHOTOS.items()}
