"""Curated pinyin + English glossary, shared with the card maker.

`cardmaker/data/characters.json` is the single source of truth for curated
readings — it used to be duplicated verbatim across this package's
``pinyin_data.py`` and ``character_dict.py``. Kahoot just reads it.

Characters/words missing from the curated glossary still get a pinyin
reading (via `pypinyin`) so quiz generation never hard-fails, but they have
no curated English meaning — a warning is raised so the gap gets noticed
and ideally fixed upstream in the shared glossary file.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from pypinyin import Style, pinyin as _pypinyin

DEFAULT_GLOSSARY_PATH = (
    Path(__file__).resolve().parents[2] / "cardmaker" / "data" / "characters.json"
)


@dataclass(frozen=True)
class Entry:
    text: str
    pinyin: str
    english: Optional[str]
    curated: bool


def load_glossary(path: Path = DEFAULT_GLOSSARY_PATH) -> Dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_pinyin(text: str) -> str:
    syllables = _pypinyin(text, style=Style.TONE, errors=lambda chars: chars)
    return "".join(s[0] for s in syllables)


def resolve(text: str, glossary: Dict[str, dict]) -> Entry:
    curated = glossary.get(text)
    if curated is not None:
        return Entry(text=text, pinyin=curated["pinyin"], english=curated["english"], curated=True)
    warnings.warn(
        f"{text!r} is not in the curated glossary ({DEFAULT_GLOSSARY_PATH.name}); "
        "using a computed pinyin reading with no English meaning. Add a curated "
        "entry there to fix this.",
        stacklevel=2,
    )
    return Entry(text=text, pinyin=compute_pinyin(text), english=None, curated=False)
