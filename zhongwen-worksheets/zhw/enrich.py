"""
Enrichment: fills derived fields on CharEntry from open data.

Sources
  - pypinyin                        -> pinyin (fallback only; textbook wins)
  - makemeahanzi/dictionary.txt     -> radical, decomposition, English definition
  - makemeahanzi/graphics.txt       -> stroke count + stroke-order SVG paths
    (makemeahanzi is CC BY 4.0 — attribute it in any published product)

All enrichment is a FALLBACK. If the textbook supplies a value, it is kept.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

VENDOR = Path(__file__).resolve().parent.parent / "vendor"
IDS_OPERATORS = set("⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻？")


# --------------------------------------------------------------------------
# makemeahanzi
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _dictionary() -> Dict[str, dict]:
    p = VENDOR / "dictionary.txt"
    if not p.exists():
        return {}
    out = {}
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out[d["character"]] = d
    return out


@lru_cache(maxsize=1)
def _graphics() -> Dict[str, dict]:
    p = VENDOR / "graphics.txt"
    if not p.exists():
        return {}
    out = {}
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out[d["character"]] = d
    return out


def stroke_count(ch: str) -> int:
    g = _graphics().get(ch)
    return len(g["strokes"]) if g else 0


def strokes(ch: str) -> List[str]:
    """SVG path data for each stroke, in stroke order."""
    g = _graphics().get(ch)
    return list(g["strokes"]) if g else []


def radical(ch: str) -> str:
    d = _dictionary().get(ch)
    return d.get("radical", "") if d else ""


def decomposition(ch: str) -> str:
    d = _dictionary().get(ch)
    return d.get("decomposition", "") if d else ""


def definition(ch: str) -> str:
    d = _dictionary().get(ch)
    return (d.get("definition") or "") if d else ""


def components(ch: str) -> List[str]:
    """Top-level components from the IDS decomposition, operators stripped."""
    dec = decomposition(ch)
    parts = [c for c in dec if c not in IDS_OPERATORS and c != ch]
    seen, out = set(), []
    for c in parts:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


# --------------------------------------------------------------------------
# pinyin
# --------------------------------------------------------------------------

def readings(ch: str) -> List[str]:
    """All dictionary readings for a single character."""
    try:
        from pypinyin import pinyin, Style
    except ImportError:
        return []
    got = pinyin(ch, style=Style.TONE, heteronym=True)
    return got[0] if got else []


def is_heteronym(ch: str) -> bool:
    """多音字 — asking for 'the' pinyin of one of these in isolation is unfair."""
    return len(readings(ch)) > 1


def auto_pinyin(text: str) -> str:
    try:
        from pypinyin import pinyin, Style
    except ImportError:
        return ""
    return " ".join(p[0] for p in pinyin(text, style=Style.TONE, heteronym=False))


TONE_MAP = str.maketrans({
    "ā": "a", "á": "a", "ǎ": "a", "à": "a",
    "ē": "e", "é": "e", "ě": "e", "è": "e",
    "ī": "i", "í": "i", "ǐ": "i", "ì": "i",
    "ō": "o", "ó": "o", "ǒ": "o", "ò": "o",
    "ū": "u", "ú": "u", "ǔ": "u", "ù": "u",
    "ǖ": "ü", "ǘ": "ü", "ǚ": "ü", "ǜ": "ü",
})


def strip_tone(py: str) -> str:
    return py.translate(TONE_MAP)


TONE_NUMBERS = {
    "āēīōūǖ": 1, "áéíóúǘ": 2, "ǎěǐǒǔǚ": 3, "àèìòùǜ": 4,
}


def tone_of(py: str) -> int:
    for marks, n in TONE_NUMBERS.items():
        if any(m in py for m in marks):
            return n
    return 5  # neutral


# --------------------------------------------------------------------------
# Similar-character detection (形近字) — derived, for distractors
# --------------------------------------------------------------------------

def similarity(a: str, b: str) -> float:
    """Crude visual-similarity score in [0,1] for 形近字 distractor picking."""
    if a == b:
        return 0.0
    ca, cb = set(components(a)), set(components(b))
    score = 0.0
    if ca and cb:
        score += 0.6 * len(ca & cb) / max(1, len(ca | cb))
    if radical(a) and radical(a) == radical(b):
        score += 0.25
    sa, sb = stroke_count(a), stroke_count(b)
    if sa and sb and abs(sa - sb) <= 1:
        score += 0.15
    return round(score, 3)


def nearest_lookalikes(ch: str, pool: List[str], n: int = 3) -> List[str]:
    ranked = sorted(((similarity(ch, p), p) for p in pool if p != ch), reverse=True)
    return [p for s, p in ranked[:n] if s > 0]


def homophones(ch: str, pool: List[str], pinyin_of) -> List[str]:
    base = strip_tone(pinyin_of(ch))
    return [p for p in pool if p != ch and strip_tone(pinyin_of(p)) == base]


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def enrich_char(entry) -> None:
    """Fill derived fields in place. Textbook-supplied values are preserved.

    Records which fields were machine-derived in `entry.derived`, so question
    types that need a textbook-authoritative value can refuse to use them.
    """
    ch = entry.char
    entry.derived = set(getattr(entry, "derived", set()) or set())
    for f in ("pinyin", "radical", "decomposition", "gloss"):
        if not getattr(entry, f, ""):
            entry.derived.add(f)
    if not entry.stroke_count:
        entry.derived.add("stroke_count")
    if not entry.pinyin:
        entry.pinyin = auto_pinyin(ch)
    if not entry.radical:
        entry.radical = radical(ch)
    if not entry.decomposition:
        entry.decomposition = decomposition(ch)
    if not entry.stroke_count:
        entry.stroke_count = stroke_count(ch)
    if not entry.components:
        entry.components = components(ch)
    if not entry.gloss:
        d = definition(ch)
        if d:
            entry.gloss = d.split(";")[0].strip()[:48]


def enrich_corpus(corpus) -> dict:
    """Enrich every character; return a coverage report."""
    missing_stroke, missing_gloss = [], []
    for ls in corpus.lessons:
        for c in ls.chars:
            enrich_char(c)
            if not c.stroke_count:
                missing_stroke.append(c.char)
            if not c.gloss:
                missing_gloss.append(c.char)
        for w in ls.words:
            if not w.pinyin:
                w.pinyin = auto_pinyin(w.word)
    return {
        "chars_total": sum(len(l.chars) for l in corpus.lessons),
        "missing_stroke_data": missing_stroke,
        "missing_gloss": missing_gloss,
    }
