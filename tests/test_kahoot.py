"""Tests for the Kahoot quiz generator (chinese_tools.kahoot)."""
import random
import warnings

import pytest

from chinese_tools.kahoot.generator import build_questions, mix_lessons
from chinese_tools.kahoot.glossary import compute_pinyin, load_glossary, resolve
from chinese_tools.kahoot.models import Lesson, LessonError, Question
from chinese_tools.kahoot.spreadsheet import validate, write_xlsx

GLOSSARY = load_glossary()


def make_lesson(**overrides):
    data = {
        "title": "test lesson",
        "mode": "hanzi_to_meaning",
        "question_template": 'What does "{prompt}" mean?',
        "items": ["花", "园", "门", "前", "个"],
        "choices": 3,
        "time_limit": 20,
        "seed": 1,
    }
    data.update(overrides)
    return Lesson.from_dict(data)


def test_glossary_resolves_curated_entry():
    entry = resolve("花", GLOSSARY)
    assert entry.curated
    assert entry.pinyin == "huā"
    assert entry.english == "flower; blossom"


def test_glossary_falls_back_to_computed_pinyin_with_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        entry = resolve("一", GLOSSARY)
    assert not entry.curated
    assert entry.english is None
    assert entry.pinyin == compute_pinyin("一")
    assert any("curated glossary" in str(w.message) for w in caught)


def test_lesson_rejects_missing_fields():
    with pytest.raises(LessonError):
        Lesson.from_dict({"title": "x"})


def test_lesson_rejects_bad_time_limit():
    with pytest.raises(LessonError):
        make_lesson(time_limit=15)


def test_lesson_rejects_choices_out_of_range():
    with pytest.raises(LessonError):
        make_lesson(choices=5)


def test_lesson_requires_prompt_placeholder():
    with pytest.raises(LessonError):
        make_lesson(question_template="no placeholder here")


def test_build_questions_is_deterministic_for_a_given_seed():
    lesson = make_lesson()
    q1 = build_questions(lesson, GLOSSARY, random.Random(lesson.resolved_seed()))
    q2 = build_questions(lesson, GLOSSARY, random.Random(lesson.resolved_seed()))
    assert [(q.text, q.choices, q.correct_index) for q in q1] == [
        (q.text, q.choices, q.correct_index) for q in q2
    ]


def test_build_questions_correct_answer_is_actually_in_the_choices():
    lesson = make_lesson()
    questions = build_questions(lesson, GLOSSARY, random.Random(42))
    for q in questions:
        assert 1 <= q.correct_index <= len(q.choices)
        correct_text = q.choices[q.correct_index - 1]
        assert correct_text  # non-empty


def test_correct_answer_slot_is_not_always_column_1():
    # the old implementation always put the correct answer in column 1 —
    # regenerate many times and confirm the slot actually varies.
    lesson = make_lesson(items=["花", "园", "门", "前", "个", "他", "后", "外"])
    seen_slots = set()
    for seed in range(30):
        for q in build_questions(lesson, GLOSSARY, random.Random(seed)):
            seen_slots.add(q.correct_index)
    assert seen_slots != {1}


def test_lesson_rejects_more_choices_than_items():
    with pytest.raises(LessonError):
        Lesson.from_dict(
            {
                "title": "too few",
                "mode": "hanzi_to_meaning",
                "question_template": "{prompt}",
                "items": ["花", "园"],
                "choices": 4,
            }
        )


def test_build_questions_raises_when_distractors_collapse_after_dedupe():
    # two items sharing an English meaning must not silently produce a
    # question with a duplicate answer choice — it should fail loudly instead.
    glossary = {
        "A": {"pinyin": "a1", "english": "same meaning"},
        "B": {"pinyin": "b1", "english": "same meaning"},
        "C": {"pinyin": "c1", "english": "unique meaning"},
    }
    lesson = Lesson.from_dict(
        {
            "title": "dedupe test",
            "mode": "hanzi_to_meaning",
            "question_template": "{prompt}?",
            "items": ["A", "B", "C"],
            "choices": 3,
        }
    )
    with pytest.raises(LessonError):
        build_questions(lesson, glossary, random.Random(1))


def test_hanzi_to_meaning_requires_curated_english():
    lesson = make_lesson(items=["花", "一", "园", "前", "个"], choices=2)
    with pytest.raises(LessonError, match="curated English meaning"):
        build_questions(lesson, GLOSSARY, random.Random(1))


def test_mix_lessons_pools_and_samples():
    lesson_a = make_lesson(title="a", seed=1)
    lesson_b = make_lesson(title="b", items=["公园", "可爱", "玫瑰", "菊花", "兰花"], seed=2)
    mixed = mix_lessons([lesson_a, lesson_b], GLOSSARY, count=4, seed=7)
    assert len(mixed) == 4


def test_validate_flags_overlong_question_and_answer():
    lesson = make_lesson(question_template='{prompt}' + "x" * 130)
    questions = build_questions(lesson, GLOSSARY, random.Random(1))
    errors = validate(questions)
    assert any("over the 120 limit" in e for e in errors)


def test_write_xlsx_roundtrip(tmp_path):
    import zipfile

    lesson = make_lesson()
    questions = build_questions(lesson, GLOSSARY, random.Random(lesson.resolved_seed()))
    out = tmp_path / "quiz.xlsx"
    write_xlsx(out, questions)
    assert out.exists() and out.stat().st_size > 0
    assert zipfile.is_zipfile(out)  # .xlsx is a zip container


def test_write_xlsx_truncates_overlong_text_instead_of_failing(tmp_path):
    # legacy cedict-style meanings can run well past 75 chars (e.g. 看's full
    # definition) — write_xlsx should truncate+warn rather than hard-fail.
    lesson = make_lesson(question_template='{prompt}' + "x" * 130)
    questions = build_questions(lesson, GLOSSARY, random.Random(1))
    with pytest.warns(UserWarning, match="truncated"):
        write_xlsx(tmp_path / "long.xlsx", questions)


def test_write_xlsx_refuses_questions_fitting_cant_fix():
    bad = [Question(text="ok", choices=["a", "b"], time_limit=20, correct_index=5)]
    with pytest.raises(LessonError):
        write_xlsx("/dev/null", bad)
