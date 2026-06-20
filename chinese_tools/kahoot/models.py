"""Lesson input format and generated question records."""
from __future__ import annotations

import json
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

Mode = Literal["hanzi_to_meaning", "hanzi_to_pinyin", "pinyin_to_meaning"]

# Kahoot only accepts these exact time limits (seconds) in its bulk-import sheet.
ALLOWED_TIME_LIMITS = {5, 10, 20, 30, 60, 90, 120, 240}


class LessonError(ValueError):
    """A lesson file is missing/malformed, or asks for something Kahoot can't import."""


@dataclass
class Lesson:
    title: str
    mode: Mode
    question_template: str
    items: List[str]
    choices: int = 4
    time_limit: int = 20
    seed: Optional[int] = None

    def resolved_seed(self) -> int:
        if self.seed is not None:
            return self.seed
        return zlib.crc32(self.title.encode("utf-8"))

    @classmethod
    def from_file(cls, path: Path) -> "Lesson":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, source=str(path))

    @classmethod
    def from_dict(cls, data: dict, source: str = "<dict>") -> "Lesson":
        required = ["title", "mode", "question_template", "items"]
        missing = [k for k in required if k not in data]
        if missing:
            raise LessonError(f"{source}: missing required field(s): {', '.join(missing)}")

        mode = data["mode"]
        if mode not in ("hanzi_to_meaning", "hanzi_to_pinyin", "pinyin_to_meaning"):
            raise LessonError(f"{source}: unknown mode {mode!r}")

        items = data["items"]
        if not isinstance(items, list) or len(items) < 2:
            raise LessonError(f"{source}: 'items' must be a list of at least 2 entries")

        choices = int(data.get("choices", 4))
        if not 2 <= choices <= 4:
            raise LessonError(f"{source}: 'choices' must be between 2 and 4 (Kahoot's limit)")
        if choices > len(items):
            raise LessonError(
                f"{source}: 'choices' ({choices}) can't exceed the number of items ({len(items)})"
            )

        time_limit = int(data.get("time_limit", 20))
        if time_limit not in ALLOWED_TIME_LIMITS:
            raise LessonError(
                f"{source}: time_limit {time_limit} isn't one of Kahoot's allowed values "
                f"({sorted(ALLOWED_TIME_LIMITS)})"
            )

        if "{prompt}" not in data["question_template"]:
            raise LessonError(f"{source}: question_template must contain a {{prompt}} placeholder")

        return cls(
            title=data["title"],
            mode=mode,
            question_template=data["question_template"],
            items=items,
            choices=choices,
            time_limit=time_limit,
            seed=data.get("seed"),
        )


@dataclass
class Question:
    text: str
    choices: List[str]
    time_limit: int
    correct_index: int  # 1-based column, matching Kahoot's "Correct answer(s)" column
