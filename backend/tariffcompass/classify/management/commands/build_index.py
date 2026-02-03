"""manage.py build_index: clean the rulings, write the label report, and build the search indexes.

    manage.py build_index            # full corpus from data/ (after make fetch-data)
    manage.py build_index --sample   # the committed fixtures only (what CI and a fresh checkout use)

Writes data/rulings/rulings_clean.jsonl (the cleaned corpus every later step reads), data/index/<full|sample>/
and classify/artifacts/labels_report.json (the counts kept and dropped, committed).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from tariffcompass.search import corpus, engine


class Command(BaseCommand):
    help = "Clean the rulings and build the Tantivy indexes over rulings and tariff text"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--sample", action="store_true", help="index the committed fixtures only")

    def handle(self, *args, **options) -> None:
        t0 = time.perf_counter()
        sample = bool(options["sample"])
        cfg = settings.TARIFF_COMPASS
        raw = Path(str(cfg["RULINGS_PATH"]))
        if not sample and not raw.exists():
            self.stdout.write("data/rulings/rulings.jsonl not found: indexing the committed sample instead")
            sample = True
        src = Path(str(cfg["RULINGS_SAMPLE"])) if sample else raw
        rulings, report = corpus.clean(corpus.iter_jsonl(src))
        if not sample:
            corpus.save(rulings, engine.clean_corpus_path())
            out = Path(str(cfg["ARTIFACT_DIR"])) / "labels_report.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            body = asdict(report)
            body["snapshot"] = corpus.snapshot_hash(rulings)
            body["source"] = "orlandowhite/hts-cross-rulings (mirror of CBP CROSS), NY and HQ letters since 2014"
            out.write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
        us, ca = engine.load_schedules(sample=sample)
        info = engine.build_indexes(rulings, us, ca, engine.index_dir(sample))
        self.stdout.write(
            f"indexed {info['rulings']} rulings ({report.labelled} labelled, {report.citable} citable) and "
            f"{info['tariffLines']} tariff lines in {time.perf_counter() - t0:.1f}s → {engine.index_dir(sample)}"
        )
