"""Evidence uploads: spec sheets (PDF, text extracted with pypdf) and photos (read through the vision adapter).

Files are checked by their first bytes, not their name: PDF, JPEG, PNG or WebP only (`415`), at most
10 MB (`413`). They are stored under `MEDIA_ROOT/<org>/<sha256>` and never served publicly.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from tariffcompass.adapters.vision import FakeVision, VisionAdapter, sniff
from tariffcompass.catalog.models import Evidence, Product
from tariffcompass.core.errors import Problem
from tariffcompass.platform.models import Organisation, User

TEXT_LIMIT = 4000


def vision() -> VisionAdapter:
    """The offline photo reader, which recognises the seed's sample photos (and nothing else)."""
    from tariffcompass.seed.documents import photo_facts

    return FakeVision(photo_facts())


def mime_of(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return sniff(data)


def pdf_text(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return " ".join(text.split())[:TEXT_LIMIT], len(reader.pages)
    except Exception as exc:
        raise Problem(
            422,
            "validation_error",
            "We couldn't read that PDF.",
            errors=[{"field": "file", "message": "The PDF couldn't be read."}],
        ) from exc


def store(
    org: Organisation,
    data: bytes,
    *,
    file_name: str,
    kind: str | None,
    uploaded_by: User | None,
    product: Product | None = None,
    label: str = "",
) -> Evidence:
    limit = int(settings.MAX_UPLOAD_MB) * 1024 * 1024
    if len(data) > limit:
        raise Problem(413, "payload_too_large", f"Files can be up to {settings.MAX_UPLOAD_MB} MB.")
    mime = mime_of(data)
    if mime is None:
        raise Problem(415, "unsupported_media_type", "Upload a PDF spec sheet, or a JPEG, PNG or WebP photo.")
    sha = hashlib.sha256(data).hexdigest()
    rel = Path(str(org.pk)) / sha
    dest = Path(settings.MEDIA_ROOT) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    text, pages, facts, certain = "", None, [], True
    if mime == "application/pdf":
        text, pages = pdf_text(data)
        kind = kind or "spec_sheet"
    else:
        read = vision().describe(data, mime)
        facts, certain = list(read.sentences), read.certain
        kind = kind or "photo"
    return Evidence.objects.create(
        org=org,
        product=product,
        kind=kind,
        label=label or _default_label(kind, file_name),
        file_name=Path(file_name).name[:200] or sha[:12],
        path=str(rel),
        mime=mime,
        size=len(data),
        sha256=sha,
        pages=pages,
        extracted_text=text,
        photo_facts=facts,
        certain=certain,
        uploaded_by=uploaded_by,
    )


def from_upload(org: Organisation, upload: UploadedFile, **kw) -> Evidence:
    limit = int(settings.MAX_UPLOAD_MB) * 1024 * 1024
    if upload.size and upload.size > limit:
        raise Problem(413, "payload_too_large", f"Files can be up to {settings.MAX_UPLOAD_MB} MB.")
    return store(org, upload.read(), file_name=upload.name or "upload", **kw)


def _default_label(kind: str, file_name: str) -> str:
    return {"spec_sheet": "Spec sheet", "photo": "Photo", "supplier_email": "Supplier email"}.get(
        kind, Path(file_name).stem[:60] or "File"
    )


def evidence_out(e: Evidence) -> dict:
    from tariffcompass.catalog.models import EVIDENCE_KINDS

    return {
        "id": str(e.pk),
        "kind": e.kind,
        "kind_label": dict(EVIDENCE_KINDS).get(e.kind, e.kind),
        "file_name": e.file_name,
        "pages": e.pages,
        "extracted_text": e.extracted_text,
        "photo_facts": list(e.photo_facts or []),
        "certain": e.certain,
        "sha256": e.sha256,
        "uploaded_by": e.uploaded_by.full_name if e.uploaded_by else "Tariff Compass",
        "uploaded_at": e.uploaded_at,
    }


def file_path(e: Evidence) -> Path:
    return Path(settings.MEDIA_ROOT) / e.path
