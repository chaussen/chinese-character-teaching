"""
Data model for the 《中文》 worksheet generator.

Design rule: THIS MODULE NEVER INVENTS CURRICULUM CONTENT.
Every character, word, sentence and pattern must come from an ingested
《中文》 lesson record. Enrichment (pinyin, radical, stroke count) is derived
from open data and is clearly separated from textbook-authoritative fields.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

HANZI_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# Characters allowed inside student-facing INSTRUCTIONS regardless of lesson
# scope. Kept deliberately tiny; extend only with a deliberate decision.
INSTRUCTION_WHITELIST = set(
    "读写认连线选填在的上下里句话词字音拼部首笔画数个正确错误例如题下面把出来"
    "一二三四五六七八九十请给和是有不我你他她它们大小多少这那什么怎样"
)


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------

@dataclass
class CharEntry:
    """One 生字 as taught by 《中文》."""
    char: str
    tier: str = "write"            # "write" = 四会字 (write) | "read" = 二会字 (recognise only)
    pinyin: str = ""               # textbook reading; authoritative, overrides enrichment
    gloss: str = ""                # English gloss (teacher supplied)
    words: List[str] = field(default_factory=list)   # 词语 in this lesson using this char

    # ---- enriched (derived, never authoritative) ----
    radical: str = ""
    decomposition: str = ""
    stroke_count: int = 0
    components: List[str] = field(default_factory=list)

    book: int = 0
    lesson: int = 0
    derived: set = field(default_factory=set)   # fields filled by enrichment

    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("derived", None)
        return d


@dataclass
class WordEntry:
    word: str
    pinyin: str = ""
    gloss: str = ""
    measure_for: str = ""          # if this word is a noun taking a 量词, name it
    book: int = 0
    lesson: int = 0


@dataclass
class Lesson:
    book: int
    lesson: int
    title: str = ""
    chars: List[CharEntry] = field(default_factory=list)
    words: List[WordEntry] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)     # 句型, e.g. "…是…的"
    sentences: List[str] = field(default_factory=list)    # textbook example sentences
    passage: str = ""                                     # optional 课文/阅读段落
    antonyms: List[List[str]] = field(default_factory=list)   # [["大","小"], ...]
    measures: List[List[str]] = field(default_factory=list)   # [["本","书"], ...]
    # ---- teacher-authored items: the only source for judgement-based types ----
    cloze: List[List[str]] = field(default_factory=list)        # [[sentence_with_＿＿, answer]]
    truefalse: List[List] = field(default_factory=list)         # [[statement, true?]]
    comprehension: List[List[str]] = field(default_factory=list)  # [[question, answer]]

    @property
    def key(self) -> str:
        return f"{self.book}.{self.lesson}"

    @property
    def label(self) -> str:
        t = f"　{self.title}" if self.title else ""
        return f"《中文》第{cn_num(self.book)}册　第{cn_num(self.lesson)}课{t}"


CN_DIGITS = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    """Small-integer Chinese numeral (enough for books 1–12, lessons 1–30)."""
    if n < 0:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n < 20:
        return "十" + (CN_DIGITS[n % 10] if n % 10 else "")
    if n < 100:
        return CN_DIGITS[n // 10] + "十" + (CN_DIGITS[n % 10] if n % 10 else "")
    return str(n)


# --------------------------------------------------------------------------
# Corpus
# --------------------------------------------------------------------------

class Corpus:
    """The whole ingested 《中文》 dataset."""

    def __init__(self, lessons: Optional[List[Lesson]] = None, meta: Optional[dict] = None):
        self.lessons: List[Lesson] = lessons or []
        self.meta: dict = meta or {}
        self._reindex()

    # ---- io ----

    @classmethod
    def load(cls, path: str | Path) -> "Corpus":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        lessons = []
        for lr in raw.get("lessons", []):
            b, l = lr["book"], lr["lesson"]
            chars = [CharEntry(book=b, lesson=l, **c) for c in lr.get("chars", [])]
            words = [WordEntry(book=b, lesson=l, **w) for w in lr.get("words", [])]
            lessons.append(Lesson(
                book=b, lesson=l, title=lr.get("title", ""),
                chars=chars, words=words,
                patterns=lr.get("patterns", []),
                sentences=lr.get("sentences", []),
                passage=lr.get("passage", ""),
                antonyms=lr.get("antonyms", []),
                measures=lr.get("measures", []),
                cloze=lr.get("cloze", []),
                truefalse=lr.get("truefalse", []),
                comprehension=lr.get("comprehension", []),
            ))
        lessons.sort(key=lambda x: (x.book, x.lesson))
        return cls(lessons, raw.get("meta", {}))

    @classmethod
    def load_many(cls, paths: Iterable[str | Path]) -> "Corpus":
        """Merge several per-book corpus files (e.g. book7.json, book8.json,
        book9.json) into one Corpus so a Scope can span multiple books —
        needed to pull review characters from books a class already
        finished."""
        lessons: List[Lesson] = []
        sources: List[dict] = []
        seen: Dict[str, str] = {}
        for p in paths:
            c = cls.load(p)
            for ls in c.lessons:
                if ls.key in seen:
                    raise ValueError(
                        f"lesson {ls.key} appears in both {seen[ls.key]} and {p}")
                seen[ls.key] = str(p)
                lessons.append(ls)
            sources.append({"path": str(p), **c.meta})
        lessons.sort(key=lambda x: (x.book, x.lesson))
        return cls(lessons, {"sources": sources})

    def save(self, path: str | Path) -> None:
        out = {"meta": self.meta, "lessons": []}
        for ls in self.lessons:
            out["lessons"].append({
                "book": ls.book, "lesson": ls.lesson, "title": ls.title,
                "chars": [{k: v for k, v in c.to_json().items()
                           if k not in ("book", "lesson")} for c in ls.chars],
                "words": [{"word": w.word, "pinyin": w.pinyin, "gloss": w.gloss,
                           "measure_for": w.measure_for} for w in ls.words],
                "patterns": ls.patterns, "sentences": ls.sentences,
                "passage": ls.passage, "antonyms": ls.antonyms, "measures": ls.measures,
                "cloze": ls.cloze,
                "truefalse": ls.truefalse, "comprehension": ls.comprehension,
            })
        Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- indexing ----

    def _reindex(self) -> None:
        self.by_key: Dict[str, Lesson] = {ls.key: ls for ls in self.lessons}

    def get(self, book: int, lesson: int) -> Lesson:
        k = f"{book}.{lesson}"
        if k not in self.by_key:
            raise KeyError(f"Lesson {k} not in corpus. Ingest it first.")
        return self.by_key[k]

    def upsert(self, lesson: Lesson) -> None:
        self.lessons = [l for l in self.lessons if l.key != lesson.key] + [lesson]
        self.lessons.sort(key=lambda x: (x.book, x.lesson))
        self._reindex()

    def books(self) -> List[int]:
        return sorted({l.book for l in self.lessons})

    def lessons_in(self, book: int) -> List[Lesson]:
        return [l for l in self.lessons if l.book == book]


# --------------------------------------------------------------------------
# Scope — the closed-vocabulary window
# --------------------------------------------------------------------------

@dataclass
class Scope:
    """
    Resolves which content a worksheet is allowed to use.

    target   : the lessons being practised (question material is drawn from here)
    allowed  : the cumulative window a student has already met (used for
               distractors, cloze fillers, puzzle padding, reading text)
    review   : older-book lessons deliberately pulled BACK into the practised
               material (not just the distractor pool) so a sheet is not 100%
               brand-new characters — see `practice_chars()`.
    """
    target_lessons: List[Lesson]
    allowed_lessons: List[Lesson]
    label: str = ""
    review_lessons: List[Lesson] = field(default_factory=list)
    review_mix: List[CharEntry] = field(default_factory=list)

    @classmethod
    def build(cls, corpus: Corpus, book: int, lessons: Iterable[int],
              vocabulary: str = "cumulative", review: Optional[dict] = None,
              seed: int = 0) -> "Scope":
        lessons = sorted(set(lessons))
        target = [corpus.get(book, l) for l in lessons]
        if vocabulary == "lesson":
            allowed = list(target)
        elif vocabulary == "book":
            allowed = [l for l in corpus.lessons_in(book) if l.lesson <= max(lessons)]
        else:  # cumulative — everything up to and including the last target lesson
            allowed = [l for l in corpus.lessons
                       if (l.book, l.lesson) <= (book, max(lessons))]
        lbl = f"第{cn_num(book)}册　第" + "、".join(cn_num(l) for l in lessons) + "课"

        review = review or {}
        review_books = set(review.get("books") or [])
        review_lessons = sorted(
            (l for l in corpus.lessons if l.book in review_books),
            key=lambda l: (l.book, l.lesson))

        scope = cls(target, allowed, lbl, review_lessons=review_lessons)
        scope._mix_review(review, seed, book, lessons)
        return scope

    def _mix_review(self, review: dict, seed: int, book: int,
                     lessons: List[int]) -> None:
        """Pick a fixed, reproducible set of review characters from
        `review_lessons` — decided once per build (same seed => same mix),
        not resampled per section, so 'today's review characters' is one
        stable list shared across every section of the sheet."""
        if not self.review_lessons:
            self.review_mix = []
            return
        tier = review.get("tier", "write")
        pool, seen = [], set()
        for ls in self.review_lessons:
            for c in ls.chars:
                if tier and c.tier != tier:
                    continue
                if c.char in seen:
                    continue
                seen.add(c.char)
                pool.append(c)
        n = review.get("count")
        if n is None:
            ratio = float(review.get("ratio") or 0)
            new_n = len(self.target_chars(tier))
            n = round(new_n * ratio / (1 - ratio)) if 0 < ratio < 1 else 0
        n = max(0, min(int(n), len(pool)))
        rng = random.Random(f"review:{seed}:{book}:{'-'.join(map(str, lessons))}")
        self.review_mix = rng.sample(pool, n) if n < len(pool) else pool

    # ---- material drawn from TARGET lessons ----

    def target_chars(self, tier: Optional[str] = None) -> List[CharEntry]:
        out = [c for ls in self.target_lessons for c in ls.chars]
        if tier:
            out = [c for c in out if c.tier == tier]
        return out

    def target_words(self) -> List[WordEntry]:
        return [w for ls in self.target_lessons for w in ls.words]

    def target_sentences(self) -> List[str]:
        return [s for ls in self.target_lessons for s in ls.sentences]

    def target_patterns(self) -> List[str]:
        return [p for ls in self.target_lessons for p in ls.patterns]

    def target_antonyms(self) -> List[List[str]]:
        return [a for ls in self.target_lessons for a in ls.antonyms]

    def target_measures(self) -> List[List[str]]:
        return [m for ls in self.target_lessons for m in ls.measures]

    def target_groups(self) -> dict:
        g = {}
        for ls in self.target_lessons:
            g.update(ls.groups)
        return g

    def allowed_groups(self) -> dict:
        g = {}
        for ls in self.allowed_lessons:
            g.update(ls.groups)
        return g

    def target_authored(self, field_name: str) -> List:
        out = []
        for ls in self.target_lessons:
            out += getattr(ls, field_name, [])
        return out

    def target_passages(self) -> List[str]:
        return [ls.passage for ls in self.target_lessons if ls.passage.strip()]

    # ---- review characters, deliberately mixed back into practice ----

    def review_chars(self, tier: Optional[str] = None) -> List[CharEntry]:
        out = list(self.review_mix)
        if tier:
            out = [c for c in out if c.tier == tier]
        return out

    def practice_chars(self, tier: Optional[str] = None) -> List[CharEntry]:
        """What question generators actually sample from: the new lesson's
        characters PLUS the reproducible review mix from older books."""
        return self.target_chars(tier) + self.review_chars(tier)

    # ---- material drawn from the ALLOWED window ----

    def _known_lessons(self) -> List[Lesson]:
        """allowed_lessons + review_lessons, deduped — review characters are
        by definition already taught, so they count as known regardless of
        which `vocabulary` window (lesson/book/cumulative) is in effect."""
        seen: Dict[tuple, Lesson] = {}
        for ls in self.allowed_lessons + self.review_lessons:
            seen[(ls.book, ls.lesson)] = ls
        return list(seen.values())

    def allowed_chars(self) -> List[CharEntry]:
        return [c for ls in self._known_lessons() for c in ls.chars]

    def allowed_words(self) -> List[WordEntry]:
        return [w for ls in self._known_lessons() for w in ls.words]

    def allowed_charset(self) -> Set[str]:
        s = {c.char for c in self.allowed_chars()}
        for w in self.allowed_words():
            s.update(ch for ch in w.word if HANZI_RE.match(ch))
        for ls in self._known_lessons():
            for txt in ls.sentences + [ls.passage]:
                s.update(ch for ch in txt if HANZI_RE.match(ch))
        return s

    def char_index(self) -> Dict[str, CharEntry]:
        return {c.char: c for c in self.allowed_chars()}

    # ---- QA gate ----

    def leaks(self, text: str) -> Set[str]:
        """Hanzi in `text` that the student has not been taught yet."""
        allowed = self.allowed_charset() | INSTRUCTION_WHITELIST
        return {ch for ch in text if HANZI_RE.match(ch) and ch not in allowed}
