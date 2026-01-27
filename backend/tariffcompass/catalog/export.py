"""Binder exports for reasonable care: a PDF (reportlab) and a ZIP with everything behind it.

The PDF prints the record fingerprint on every page. The ZIP holds the PDF, the text of every ruling relied
on, the evidence files, the product's slice of the activity record (CSV) and a manifest with each file's
SHA-256. Both are written under `<data>/exports/<job id>/` and never served publicly.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from tariffcompass import clock, services
from tariffcompass.catalog import binder
from tariffcompass.catalog.evidence import file_path
from tariffcompass.catalog.models import Answer, Product
from tariffcompass.platform import audit, roles
from tariffcompass.platform.models import AuditEvent

INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#62625B")
RULE = colors.HexColor("#D9D9D0")
HI = colors.HexColor("#FFF3A6")


def _day(d: Any) -> str:
    if isinstance(d, datetime):
        d = clock.local(d)
    return f"{d.day} {d.strftime('%b %Y')}"


def export_root() -> Path:
    root = Path(settings.MEDIA_ROOT).parent / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _latin(text: str) -> str:
    """Helvetica covers Latin-1; swap the few typographic marks the record uses."""
    table = {"→": "->", "〃": '"', "…": "...", "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"'}
    for a, b in table.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_latin(text)), style)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
    return {
        "title": ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=20),
        "h": ParagraphStyle("h", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=10),
        "body": body,
        "small": ParagraphStyle("small", parent=body, fontSize=7.5, leading=10, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=body, fontSize=7.5, leading=9.5),
    }


def _table(rows: list[list[Any]], widths: list[float], *, header: bool = True) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5), ("LINEBELOW", (0, 0), (-1, 0), 1, INK)]
    t.setStyle(TableStyle(style))
    return t


def build_pdf(product: Product, data: dict[str, Any]) -> tuple[bytes, int]:
    s = _styles()
    record_fp = data["record"]["fingerprint"]
    pages = {"n": 0}
    today = clock.today()

    def on_page(canvas, doc) -> None:
        pages["n"] += 1
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            0.75 * inch,
            0.5 * inch,
            _latin(f"Tariff Compass · {product.sku} · record fingerprint {record_fp} · exported {today.isoformat()}"),
        )
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.8 * inch,
        title=f"Binder {product.sku}",
        author=product.org.name,
        creator="Tariff Compass",
        invariant=1,
    )
    story: list[Any] = [
        _p("REASONABLE-CARE RECORD", s["small"]),
        _p(f"{product.title} ({product.sku})", s["title"]),
        _p(f"{product.org.name} · made in {data['product']['made_in_label']}", s["body"]),
        _p(
            f"Opened {_day(data['opened_on'])} · {len(data['versions'])} versions · "
            f"kept until {_day(data['kept_until'])}",
            s["body"],
        ),
        _p(data["retention_note"], s["small"]),
        Spacer(1, 6),
    ]
    if data["approval"]:
        story.append(_p(data["approval"]["sentence"], s["body"]))
    story.append(_p("Versions", s["h"]))
    rows: list[list[Any]] = [
        ["v", "What happened", "When", "US code", "Canada code", "Decided by", "Why", "Fingerprint"]
    ]
    for v in data["versions"]:
        who = v["decided_by"]["full_name"] if v["decided_by"] else ""
        rows.append(
            [
                str(v["n"]),
                _p(v["kind_label"] + (" (current)" if v["current"] else ""), s["cell"]),
                _day(v["at"]),
                v["us_code"] or "",
                v["ca_code"] or "",
                _p(who, s["cell"]),
                _p(v["why"], s["cell"]),
                v["fingerprint"],
            ]
        )
    story.append(
        _table(
            rows,
            [0.25 * inch, 0.9 * inch, 0.65 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 1.65 * inch, 0.95 * inch],
        )
    )
    story.append(_p("What each version rested on", s["h"]))
    for v in data["versions"]:
        fact = v["deciding_fact"]
        parts = [f"v{v['n']}:"]
        if fact:
            parts.append(f"{fact['label']}: {fact['value']} ({fact['source_note']}).")
        if v["rulings_relied"]:
            parts.append(
                "Rulings relied on: " + ", ".join(f"{r['id']} ({r['status_label']})" for r in v["rulings_relied"]) + "."
            )
        if v["evidence"]:
            parts.append("Evidence: " + ", ".join(v["evidence"]) + ".")
        story.append(_p(" ".join(parts), s["body"]))
    if data["entries"]:
        story.append(_p("Entries using this code", s["h"]))
        erows: list[list[Any]] = [["Entry", "Country", "Entered", "Code", "Duty paid"]]
        for e in data["entries"]:
            erows.append(
                [
                    e["entry_number"],
                    e["country"],
                    _day(e["entered_on"]),
                    e["code"],
                    f"{e['duty_paid']['currency']} {e['duty_paid']['amount']}",
                ]
            )
        story.append(_table(erows, [1.6 * inch, 0.7 * inch, 1 * inch, 1.3 * inch, 1.4 * inch]))
    if data["evidence"]:
        story.append(_p("Evidence on file", s["h"]))
        vrows: list[list[Any]] = [["File", "Kind", "Added by", "SHA-256"]]
        for e in data["evidence"]:
            vrows.append(
                [
                    _p(e["file_name"], s["cell"]),
                    e["kind_label"],
                    _p(e["uploaded_by"], s["cell"]),
                    _p(e["sha256"], s["cell"]),
                ]
            )
        story.append(_table(vrows, [1.8 * inch, 0.9 * inch, 1.2 * inch, 3.1 * inch]))
    lm = Answer.objects.filter(product=product).order_by("-created_at").values_list("lm_label", flat=True).first()
    story += [
        _p("Record", s["h"]),
        _p(
            f"Activity chain {'verified' if data['record']['chain_verified'] else 'NOT verified'} "
            f"({data['record']['events']} events about this product). Record fingerprint {record_fp}.",
            s["body"],
        ),
    ]
    if lm:
        story.append(_p(f"Latest answer written by: {lm}.", s["small"]))
    story.append(
        _p(
            "Designed to support reasonable-care record keeping (19 U.S.C. 1484; 19 CFR Part 163; CBSA Memorandum "
            "D17-1-21). Nothing was filed automatically: a licensed customs broker approves every code before it is "
            "used on an entry.",
            s["small"],
        )
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue(), pages["n"]


def activity_csv(product: Product) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "at", "actor", "role", "action", "summary", "hash"])
    for e in AuditEvent.objects.filter(org=product.org, target_type="product", target_id=str(product.pk)).order_by(
        "id"
    ):
        w.writerow(
            [
                e.id,
                e.created_at.isoformat(),
                e.actor_name,
                roles.ROLE_LABELS.get(e.actor_role, ""),
                e.action,
                e.summary,
                e.hash,
            ]
        )
    return buf.getvalue().encode()


def build_zip(product: Product, data: dict[str, Any], pdf: bytes) -> bytes:
    files: list[tuple[str, bytes]] = [(f"binder-{product.sku}.pdf", pdf)]
    relied = sorted({r["id"] for v in data["versions"] for r in v["rulings_relied"]})
    for rid in relied:
        doc = services.retriever().ruling(rid)
        if doc is not None:
            body = f"{doc.ruling_id} · issued {doc.issued.isoformat()} · {doc.source_url}\n\n{doc.text}\n"
            files.append((f"rulings/{rid.replace(' ', '-')}.txt", body.encode()))
    for e in product.evidence.all():
        path = file_path(e)
        if path.is_file():
            files.append((f"evidence/{e.sha256[:8]}-{e.file_name}", path.read_bytes()))
    files.append(("activity.csv", activity_csv(product)))
    manifest = "\n".join(f"{hashlib.sha256(b).hexdigest()}  {name}" for name, b in files)
    files.append(
        (
            "MANIFEST.txt",
            (
                f"Tariff Compass binder export for {product.sku} ({product.org.name})\n"
                f"Record fingerprint {data['record']['fingerprint']}\n\nSHA-256 of each file:\n{manifest}\n"
            ).encode(),
        )
    )
    today = clock.today()
    when = (today.year, today.month, today.day, 0, 0, 0)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files:
            info = zipfile.ZipInfo(name, date_time=when)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content)
    return out.getvalue()


def export(product: Product, fmt: str, job_id: str) -> dict[str, Any]:
    """Write the file; returns the job result (ExportResult, camelCase like every job result) plus `path`."""
    check = audit.verify(product.org)
    data = binder.binder_out(product, chain_ok=check.ok, checked_at=datetime.fromisoformat(check.checked_at))
    pdf, pages = build_pdf(product, data)
    if fmt == "zip":
        content, name, n_pages = build_zip(product, data, pdf), f"binder-{product.sku}.zip", None
    else:
        content, name, n_pages = pdf, f"binder-{product.sku}.pdf", pages
    folder = export_root() / job_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(content)
    return {
        "path": str(path),
        "downloadUrl": f"/api/v1/exports/{job_id}/download",
        "fileName": name,
        "bytes": len(content),
        "pages": n_pages,
        "fingerprint": audit.fingerprint(hashlib.sha256(content).hexdigest()),
        "recordFingerprint": data["record"]["fingerprint"],
    }
