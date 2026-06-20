"""CLI: build Kahoot bulk-import quiz spreadsheets from lesson vocabulary lists.

    python -m chinese_tools.kahoot generate \\
        chinese_tools/kahoot/lessons/lesson10_huayuan.json -o out/lesson10.xlsx
    python -m chinese_tools.kahoot mix lessons/*.json -o out/mixed.xlsx --count 20
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from .generator import build_questions, mix_lessons
from .glossary import load_glossary
from .models import Lesson, LessonError
from .spreadsheet import write_xlsx


def cmd_generate(args: argparse.Namespace) -> None:
    lesson = Lesson.from_file(Path(args.lesson))
    glossary = load_glossary()
    seed = args.seed if args.seed is not None else lesson.resolved_seed()
    questions = build_questions(lesson, glossary, random.Random(seed))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_xlsx(out, questions)
    print(f"wrote {len(questions)} questions to {out} (seed={seed})")


def cmd_mix(args: argparse.Namespace) -> None:
    glossary = load_glossary()
    lessons = [Lesson.from_file(Path(p)) for p in args.lessons]
    questions = mix_lessons(lessons, glossary, args.count, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_xlsx(out, questions)
    print(f"wrote {len(questions)} mixed questions (from {len(lessons)} lessons) to {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m chinese_tools.kahoot",
        description="Build Kahoot bulk-import quiz spreadsheets from a lesson vocabulary list.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="build one quiz from one lesson file")
    p_gen.add_argument("lesson", help="path to a lesson .json file")
    p_gen.add_argument("-o", "--output", required=True, help="output .xlsx path")
    p_gen.add_argument(
        "--seed", type=int, default=None, help="override the lesson's seed for a different shuffle"
    )
    p_gen.set_defaults(func=cmd_generate)

    p_mix = sub.add_parser(
        "mix", help="pool questions from several lessons into one combined quiz"
    )
    p_mix.add_argument("lessons", nargs="+", help="paths to lesson .json files")
    p_mix.add_argument("-o", "--output", required=True, help="output .xlsx path")
    p_mix.add_argument(
        "--count", type=int, default=0, help="total questions to sample (default: all)"
    )
    p_mix.add_argument("--seed", type=int, default=0, help="seed for the sampling/shuffle order")
    p_mix.set_defaults(func=cmd_mix)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except LessonError as e:
        parser.exit(1, f"error: {e}\n")


if __name__ == "__main__":
    main()
