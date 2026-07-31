"""
Ingest 《中文》 lesson content.

Three accepted formats — all keep the textbook as the source of truth.

1) BLOCK (easiest to type or paste from the 生字表)
       book: 3
       lesson: 1
       title: 我的社区
       write: 店 区 近 边
       read: 邮 银
       words: 商店 shāngdiàn shop / 附近 fùjìn nearby
       patterns: ……的旁边是……
       sentences: 我家附近有一个商店。| 学校在公园的旁边。
       antonyms: 大-小 | 多-少
       measures: 家-商店 | 个-公园
       passage: 我家住在……

   Multiple lessons in one file: separate with a line of `---`.

2) TSV   char <TAB> pinyin <TAB> gloss <TAB> tier <TAB> word;word
3) JSON  a corpus file, or a list of lesson dicts
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from .model import CharEntry, Lesson, WordEntry, Corpus

SPLIT_ITEMS = re.compile(r"[|/、，,；;]+")


def parse_block(text: str) -> List[Lesson]:
    lessons: List[Lesson] = []
    for chunk in re.split(r"^\s*---+\s*$", text, flags=re.M):
        if not chunk.strip():
            continue
        f = {}
        for line in chunk.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line or "：" in line:
                k, _, v = re.split(r"[:：]", line, maxsplit=1) + [""] * 0, None, None
            m = re.match(r"^([A-Za-z_]+)\s*[:：]\s*(.*)$", line)
            if m:
                key, val = m.group(1).lower(), m.group(2).strip()
                f[key] = (f.get(key, "") + " " + val).strip() if key in f else val
        if "lesson" not in f:
            continue
        ls = Lesson(book=int(f.get("book", 0)), lesson=int(f["lesson"]),
                    title=f.get("title", ""))
        for tier, key in (("write", "write"), ("read", "read"), ("write", "chars")):
            for tok in re.split(r"[\s、，,/|]+", f.get(key, "")):
                tok = tok.strip()
                if tok:
                    ls.chars.append(CharEntry(char=tok[0], tier=tier,
                                              book=ls.book, lesson=ls.lesson))
        for item in SPLIT_ITEMS.split(f.get("words", "")):
            item = item.strip()
            if not item:
                continue
            parts = item.split()
            ls.words.append(WordEntry(word=parts[0],
                                      pinyin=parts[1] if len(parts) > 1 else "",
                                      gloss=" ".join(parts[2:]),
                                      book=ls.book, lesson=ls.lesson))
        ls.patterns = [p.strip() for p in re.split(r"[|]", f.get("patterns", "")) if p.strip()]
        ls.sentences = [s.strip() for s in re.split(r"[|]", f.get("sentences", "")) if s.strip()]
        ls.passage = f.get("passage", "")
        ls.antonyms = [p.split("-") for p in re.split(r"[|，,、]", f.get("antonyms", ""))
                       if "-" in p]
        ls.measures = [p.split("-") for p in re.split(r"[|，,、]", f.get("measures", ""))
                       if "-" in p]
        lessons.append(ls)
    return lessons


def parse_tsv(text: str, book: int, lesson: int) -> List[Lesson]:
    ls = Lesson(book=book, lesson=lesson)
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        ch = cols[0].strip()
        if not ch:
            continue
        e = CharEntry(char=ch[0], book=book, lesson=lesson,
                      pinyin=cols[1].strip() if len(cols) > 1 else "",
                      gloss=cols[2].strip() if len(cols) > 2 else "",
                      tier=(cols[3].strip() or "write") if len(cols) > 3 else "write")
        if len(cols) > 4 and cols[4].strip():
            e.words = [w.strip() for w in re.split(r"[;；、,]", cols[4]) if w.strip()]
            for w in e.words:
                ls.words.append(WordEntry(word=w, book=book, lesson=lesson))
        ls.chars.append(e)
    return [ls]


def ingest_file(path: str | Path, book: int = 0, lesson: int = 0) -> List[Lesson]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        raw = json.loads(text)
        if isinstance(raw, dict) and "lessons" in raw:
            return Corpus.load(p).lessons
        raise ValueError("JSON must be a corpus file with a 'lessons' key")
    if "\t" in text and ":" not in text.splitlines()[0]:
        return parse_tsv(text, book, lesson)
    return parse_block(text)


def ad_hoc_lesson(chars: str, words: str = "", sentences: str = "",
                  title: str = "自定义练习") -> Lesson:
    """Build a throwaway lesson from characters fed straight in on the CLI."""
    ls = Lesson(book=0, lesson=0, title=title)
    for ch in chars:
        if "\u4e00" <= ch <= "\u9fff":
            ls.chars.append(CharEntry(char=ch, tier="write"))
    for w in re.split(r"[\s、，,/|;；]+", words):
        if w.strip():
            ls.words.append(WordEntry(word=w.strip()))
    ls.sentences = [s.strip() for s in re.split(r"[|]", sentences) if s.strip()]
    return ls
