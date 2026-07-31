"""
Question bank. Every question type is a registered generator function.

Adding a type is a 20-line job:

    @register("my_type", "中文名", "English name", "form",
              needs=("chars",), default_count=6)
    def my_type(ctx: Ctx) -> Question | None:
        ...

Contract:
  * return None if the scope has too little material — the build skips it
  * put EVERY Hanzi the student has to read into Question.student_hanzi
  * never emit a character outside ctx.scope.allowed_charset()
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..model import Scope, CharEntry, WordEntry
from ..render import Question

CATEGORIES = {
    "form": "字形 Character form",
    "sound": "拼音 Pinyin & sound",
    "meaning": "词义 Meaning & vocabulary",
    "sentence": "句子 Sentence & grammar",
    "reading": "阅读 Reading",
    "puzzle": "游戏 Puzzle & game",
    "production": "书写 Production",
}


@dataclass
class TypeSpec:
    id: str
    name_zh: str
    name_en: str
    category: str
    fn: Callable
    needs: Tuple[str, ...] = ()
    default_count: int = 6
    marks_each: int = 1
    minutes_each: float = 0.4
    blurb: str = ""
    confidence: str = "verified"
    risk: str = ""


_TIMING: Dict[str, float] = {}
TIMING_META = {"overhead": 25.0, "settling": 3.0}


def load_timing(path="data/timing.json") -> None:
    """Seconds-per-item per type. Single source of truth for every duration."""
    import json, pathlib as _p
    f = _p.Path(path)
    if not f.exists():
        return
    d = json.loads(f.read_text(encoding="utf-8"))
    TIMING_META["overhead"] = float(d.get("_overhead_seconds_per_section", 25))
    TIMING_META["settling"] = float(d.get("_settling_minutes", 3))
    for k, v in d.items():
        if not k.startswith("_"):
            _TIMING[k] = float(v)


def seconds_per_item(type_id: str, fallback: float) -> float:
    return _TIMING.get(type_id, fallback * 60.0)


CONFIDENCE = {
    "verified": "key is machine-provable from the data",
    "authored": "key comes from teacher-supplied items",
    "open":     "no single key; marked against stated criteria",
    "derived":  "key depends on auto-enrichment that may not match the textbook",
}

REGISTRY: Dict[str, TypeSpec] = {}


def register(id_: str, name_zh: str, name_en: str, category: str,
             needs: Sequence[str] = (), default_count: int = 6,
             marks_each: int = 1, minutes_each: float = 0.4, blurb: str = "",
             confidence: str = "verified", risk: str = ""):
    def deco(fn):
        REGISTRY[id_] = TypeSpec(id_, name_zh, name_en, category, fn,
                                 tuple(needs), default_count, marks_each,
                                 minutes_each, blurb, confidence, risk)
        return fn
    return deco


def types_by_category() -> Dict[str, List[TypeSpec]]:
    out: Dict[str, List[TypeSpec]] = {}
    for t in REGISTRY.values():
        out.setdefault(t.category, []).append(t)
    for v in out.values():
        v.sort(key=lambda t: t.id)
    return out


# --------------------------------------------------------------------------
# Generator context
# --------------------------------------------------------------------------

@dataclass
class Ctx:
    scope: Scope
    rng: random.Random
    params: dict = field(default_factory=dict)
    count: int = 6

    # ---- params ----
    def p(self, key: str, default=None):
        return self.params.get(key, default)

    # ---- material ----
    def chars(self, tier: Optional[str] = None) -> List[CharEntry]:
        return self.scope.practice_chars(tier)

    def write_chars(self) -> List[CharEntry]:
        c = self.scope.practice_chars("write")
        return c or self.scope.practice_chars()

    def words(self) -> List[WordEntry]:
        return self.scope.target_words()

    def all_chars(self) -> List[CharEntry]:
        return self.scope.allowed_chars()

    def all_words(self) -> List[WordEntry]:
        return self.scope.allowed_words()

    # ---- sampling (deterministic under the seed) ----
    def pick(self, seq: Sequence, n: int) -> List:
        seq = list(seq)
        if not seq:
            return []
        if n >= len(seq):
            out = seq[:]
            self.rng.shuffle(out)
            return out
        return self.rng.sample(seq, n)

    def shuffled(self, seq: Sequence) -> List:
        out = list(seq)
        self.rng.shuffle(out)
        return out

    def distractors(self, exclude: Sequence[str], n: int,
                    pool: Optional[Sequence[str]] = None) -> List[str]:
        ex = set(exclude)
        p = [c for c in (pool or [c.char for c in self.all_chars()]) if c not in ex]
        return self.pick(p, n)

    def teacher_pinyin(self, ch: str):
        """Pinyin only if the textbook gave it. None if it was auto-filled."""
        e = self.scope.char_index().get(ch)
        if e and e.pinyin and "pinyin" not in getattr(e, "derived", set()):
            return e.pinyin
        return None

    def unambiguous_pinyin(self, ch: str):
        """Reject 多音字 and auto-filled readings — both make the key arguable."""
        from .. import enrich
        py = self.teacher_pinyin(ch)
        if py is None:
            return None
        return None if enrich.is_heteronym(ch) else py

    def pinyin_of(self, ch: str) -> str:
        idx = self.scope.char_index()
        if ch in idx and idx[ch].pinyin:
            return idx[ch].pinyin
        from .. import enrich
        return enrich.auto_pinyin(ch)


# import submodules so their @register decorators run
from . import form, sound, meaning, sentence, reading, puzzle, drill  # noqa: E402,F401
