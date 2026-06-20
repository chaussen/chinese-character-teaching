"""Validate Questions against Kahoot's bulk-import spec and write the .xlsx.

Kahoot's importer only accepts .xlsx (a plain .csv upload is rejected), so
this writes straight to .xlsx with `xlsxwriter` — no CSV intermediate step.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import List

from xlsxwriter import Workbook

from .models import ALLOWED_TIME_LIMITS, LessonError, Question

MAX_QUESTION_LEN = 120
MAX_ANSWER_LEN = 75

COLUMNS = [
    "#",
    "Question - max 120 characters",
    "Answer 1 - max 75 characters",
    "Answer 2 - max 75 characters",
    "Answer 3 - max 75 characters",
    "Answer 4 - max 75 characters",
    "Time limit (sec) - 5, 10, 20, 30, 60, 90, 120, or 240 secs",
    "Correct answer(s) - choose at least one",
]


def validate(questions: List[Question]) -> List[str]:
    errors = []
    for n, q in enumerate(questions, start=1):
        if len(q.text) > MAX_QUESTION_LEN:
            errors.append(
                f"question {n}: text is {len(q.text)} chars, over the "
                f"{MAX_QUESTION_LEN} limit: {q.text!r}"
            )
        if not 2 <= len(q.choices) <= 4:
            errors.append(f"question {n}: has {len(q.choices)} answer choices, Kahoot needs 2-4")
        for a_n, answer in enumerate(q.choices, start=1):
            if len(answer) > MAX_ANSWER_LEN:
                errors.append(
                    f"question {n} answer {a_n}: is {len(answer)} chars, over the "
                    f"{MAX_ANSWER_LEN} limit: {answer!r}"
                )
        if q.time_limit not in ALLOWED_TIME_LIMITS:
            allowed = sorted(ALLOWED_TIME_LIMITS)
            errors.append(f"question {n}: time_limit {q.time_limit} isn't one of {allowed}")
        if not 1 <= q.correct_index <= len(q.choices):
            errors.append(
                f"question {n}: correct_index {q.correct_index} is out of range for "
                f"{len(q.choices)} choices"
            )
    return errors


def _fit(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    truncated = text[: limit - 1].rstrip() + "…"
    warnings.warn(
        f"truncated to fit Kahoot's {limit}-char limit: {text!r} -> {truncated!r}; "
        "consider shortening the curated glossary entry instead.",
        stacklevel=2,
    )
    return truncated


def fit_to_limits(questions: List[Question]) -> List[Question]:
    """Truncate over-length text so legacy/cedict-style long definitions still
    produce a sheet Kahoot will accept, instead of hard-failing on them."""
    return [
        Question(
            text=_fit(q.text, MAX_QUESTION_LEN),
            choices=[_fit(c, MAX_ANSWER_LEN) for c in q.choices],
            time_limit=q.time_limit,
            correct_index=q.correct_index,
        )
        for q in questions
    ]


def write_xlsx(path: Path, questions: List[Question]) -> None:
    questions = fit_to_limits(questions)
    errors = validate(questions)
    if errors:
        raise LessonError(
            "refusing to write an import sheet Kahoot would reject:\n  " + "\n  ".join(errors)
        )

    workbook = Workbook(str(path))
    worksheet = workbook.add_worksheet()
    worksheet.write_row(0, 0, COLUMNS)
    for row, q in enumerate(questions, start=1):
        answers = q.choices + [""] * (4 - len(q.choices))
        worksheet.write_row(row, 0, [row, q.text, *answers, q.time_limit, q.correct_index])
    workbook.close()
