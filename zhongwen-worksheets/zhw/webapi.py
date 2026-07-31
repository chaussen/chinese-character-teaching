"""
Browser glue for the in-page (Pyodide) Worksheet Maker.

Not used by the CLI. `worksheet-maker/app.js` writes this whole `zhw` package
plus `data/*.json` into Pyodide's virtual filesystem, imports this module, and
calls `generate_worksheet(options_json)` / `list_lessons(data_paths_json)` —
both take and return plain JSON strings so nothing but immutable str crosses
the JS/Python boundary (Pyodide converts those automatically; nothing else
does, without an explicit proxy).
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Dict

from . import enrich
from .build import (DEFAULT_ALLOW, PRESETS, _annotate_minutes,
                    _group_by_category, plan_for_minutes, build_one)
from .model import Corpus, cn_num

_CORPUS_CACHE: Dict[tuple, Corpus] = {}


def _load_corpus(paths) -> Corpus:
    key = tuple(paths)
    corpus = _CORPUS_CACHE.get(key)
    if corpus is None:
        corpus = Corpus.load_many(paths) if len(paths) > 1 else Corpus.load(paths[0])
        enrich.enrich_corpus(corpus)
        _CORPUS_CACHE[key] = corpus
    return corpus


def list_lessons(data_paths_json: str) -> str:
    """Books and lessons actually present in the shipped data, so the UI never
    hardcodes what the corpus contains. Returns [{book, lessons:[{lesson,title}]}]."""
    try:
        corpus = _load_corpus(json.loads(data_paths_json))
        out = []
        for book in corpus.books():
            out.append({
                "book": book,
                "label": f"第{cn_num(book)}册",
                "lessons": [{"lesson": ls.lesson, "title": ls.title}
                           for ls in corpus.lessons_in(book)],
            })
        return json.dumps({"books": out})
    except Exception as e:                                   # noqa: BLE001
        return json.dumps({"error": str(e), "trace": traceback.format_exc()})


def generate_worksheet(options_json: str) -> str:
    """Build one worksheet from a plain options dict (the JS-side equivalent
    of a recipe file) and return {html, report} as JSON. Errors are caught and
    returned as {"error": ...} rather than raised across the JS/Python
    boundary, where a bare traceback is much less useful to the caller."""
    try:
        o = json.loads(options_json)
        corpus = _load_corpus(o["data_paths"])
        book, lessons = int(o["book"]), [int(l) for l in o["lessons"]]
        vocabulary = o.get("vocabulary", "cumulative")
        review = o.get("review") or None
        seed = int(o.get("seed", 20260731))
        allow = tuple(o.get("allow") or DEFAULT_ALLOW)
        minutes = o.get("minutes")

        plan_log = None
        if minutes:
            from .model import Scope
            probe = Scope.build(corpus, book, lessons, vocabulary,
                                review=review, seed=seed)
            sections, _, plan_log = plan_for_minutes(
                probe, seed, float(minutes), allow,
                production_share=float(o.get("production_share", 0.3)))
            sections = _group_by_category(sections)
        else:
            types = o.get("types")
            sections = ([{"type": t} for t in types] if types
                        else PRESETS[o.get("preset", "standard")])

        out_path = Path("/tmp/webapi-out.html")
        rep = build_one(
            corpus=corpus, book=book, lessons=lessons, sections=sections,
            seed=seed, out=out_path, recipe_id=o.get("id", "web"),
            vocabulary=vocabulary, title=o.get("title"),
            density=o.get("density", ""), show_key=o.get("show_key", True),
            school_line=o.get("school_line", "本校 · 内部使用 Internal use"),
            strict=False, style=o.get("style", "drill"), lang=o.get("lang", "both"),
            allow=allow, show_marks=bool(o.get("marks", False)), review=review)
        if plan_log is not None:
            _annotate_minutes(rep, float(minutes), plan_log)

        html = out_path.read_text(encoding="utf-8")
        return json.dumps({"html": html, "report": rep})
    except Exception as e:                                    # noqa: BLE001
        return json.dumps({"error": str(e), "trace": traceback.format_exc()})
