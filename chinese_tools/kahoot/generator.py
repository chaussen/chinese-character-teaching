"""Turn a Lesson + glossary into a deterministic list of multiple-choice Questions.

Two bugs in the previous implementation motivated the rewrite:
- the correct answer always landed in column 1 (never actually randomized,
  so "always pick Answer 1" was a winning strategy for students);
- nothing was seeded, so re-running the generator for the same lesson
  produced a different spreadsheet every time, making results impossible
  to reproduce or diff.
"""
from __future__ import annotations

import random
from typing import Dict, List

from .glossary import Entry, resolve
from .models import Lesson, LessonError, Question


def _prompt(entry: Entry, mode: str) -> str:
    return entry.pinyin if mode == "pinyin_to_meaning" else entry.text


def _answer(entry: Entry, mode: str) -> str:
    if mode == "hanzi_to_pinyin":
        return entry.pinyin
    if entry.english is None:
        raise LessonError(
            f"{entry.text!r} has no curated English meaning, but mode {mode!r} needs "
            "one — add it to cardmaker/data/characters.json."
        )
    return entry.english


def build_questions(
    lesson: Lesson, glossary: Dict[str, dict], rng: random.Random
) -> List[Question]:
    entries = [resolve(item, glossary) for item in lesson.items]
    answers = [_answer(e, lesson.mode) for e in entries]
    prompts = [_prompt(e, lesson.mode) for e in entries]

    questions: List[Question] = []
    need = lesson.choices - 1
    for i, entry in enumerate(entries):
        correct = answers[i]
        # dedupe so two distractors never show the same text in one question,
        # and exclude the correct answer's own text even if another item happens
        # to share it.
        pool = list(dict.fromkeys(a for j, a in enumerate(answers) if j != i and a != correct))
        if len(pool) < need:
            raise LessonError(
                f"{lesson.title}: not enough distinct distractors for {entry.text!r} "
                f"(need {need}, have {len(pool)} other items)"
            )
        distractors = rng.sample(pool, need)
        choices = distractors + [correct]
        rng.shuffle(choices)
        questions.append(
            Question(
                text=lesson.question_template.format(prompt=prompts[i]),
                choices=choices,
                time_limit=lesson.time_limit,
                correct_index=choices.index(correct) + 1,
            )
        )
    return questions


def mix_lessons(
    lessons: List[Lesson],
    glossary: Dict[str, dict],
    count: int,
    seed: int,
) -> List[Question]:
    """Pool questions from several lessons and sample/shuffle a combined deck."""
    pool: List[Question] = []
    for lesson in lessons:
        lesson_rng = random.Random(lesson.resolved_seed())
        pool.extend(build_questions(lesson, glossary, lesson_rng))

    mix_rng = random.Random(seed)
    if count <= 0 or count > len(pool):
        count = len(pool)
    selected = mix_rng.sample(pool, count)
    mix_rng.shuffle(selected)
    return selected
