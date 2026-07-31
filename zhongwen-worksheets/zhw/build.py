"""
Build worksheets.

    # from the corpus, one lesson, standard preset
    python -m zhw.build --data data/zhongwen.json --book 3 --lesson 1 --preset standard

    # every lesson in a book, one file each (auto-selects types that have material)
    python -m zhw.build --data data/zhongwen.json --book 3 --all --preset auto

    # characters fed straight in, no corpus needed
    python -m zhw.build --chars 店区近边 --words "商店 附近 旁边" --preset quick

    # a pinned recipe file (reproducible: same seed => byte-identical worksheet)
    python -m zhw.build --recipe recipes/b3l1-standard.yaml

    # list every available question type
    python -m zhw.build --list-types
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import enrich, qbank, validate

qbank.load_timing()
from .ingest import ad_hoc_lesson, ingest_file
from .model import Corpus, Lesson, Scope, cn_num
from .qbank import REGISTRY, Ctx, types_by_category
from .render import Question, render_worksheet

try:
    import yaml
except ImportError:
    yaml = None


# --------------------------------------------------------------------------
# Presets — a preset is just an ordered list of section specs
# --------------------------------------------------------------------------

def S(t, n=None, **params):
    d = {"type": t}
    if n is not None:
        d["count"] = n
    if params:
        d["params"] = params
    return d


PRESETS: Dict[str, List[dict]] = {
    "quick": [
        S("trace", 4, boxes=6), S("pinyin_write", 6), S("make_words", 4),
        S("cloze", 4),
    ],
    "standard": [
        {"type": "heading", "zh": "一、字", "en": "Characters"},
        S("trace", 6, boxes=6), S("stroke_count", 8), S("lookalike", 6),
        {"type": "heading", "zh": "二、音", "en": "Pinyin"},
        S("pinyin_write", 8), S("pinyin_read", 6), S("pinyin_match", 6),
        {"type": "heading", "zh": "三、词", "en": "Vocabulary"},
        S("make_words", 6), S("gloss_match", 6), S("word_build_boxes", 5),
        {"type": "heading", "zh": "四、句", "en": "Sentences"},
        S("cloze", 5), S("scramble", 4),
        {"type": "heading", "zh": "五、玩一玩", "en": "Puzzle"},
        S("word_search", 6),
    ],
    "full": [
        {"type": "heading", "zh": "一、字", "en": "Characters"},
        S("trace", 8, boxes=6), S("stroke_count", 8), S("lookalike", 6),
        S("minimal_pairs", 12),
        {"type": "heading", "zh": "二、音", "en": "Pinyin"},
        S("pinyin_write", 8), S("pinyin_read", 8), S("pinyin_partial", 12),
        S("tone_mark", 8), S("pinyin_match", 6), S("homophone", 4),
        {"type": "heading", "zh": "三、词", "en": "Vocabulary"},
        S("make_words", 8), S("gloss_match", 6), S("word_meaning_mcq", 5),
        S("antonym", 6), S("word_build_boxes", 6),
        {"type": "heading", "zh": "四、句", "en": "Sentences"},
        S("cloze", 6), S("scramble", 4), S("measure_word", 8),
        S("use_the_word", 6), S("pattern_write", 3),
        {"type": "heading", "zh": "五、阅读", "en": "Reading"},
        S("passage_read", 6), S("sentence_order", 4),
        {"type": "heading", "zh": "六、玩一玩", "en": "Puzzle"},
        S("word_search", 6), S("char_maze"), S("code_breaker"),
        {"type": "heading", "zh": "七、写一写", "en": "Write"},
        S("free_write"),
    ],
    "unit_test": [
        S("minimal_pairs", 12), S("pinyin_partial", 12), S("cloze", 6),
        S("use_the_word", 6), S("measure_word", 8), S("passage_read", 6),
    ],
    "revision": [
        S("pinyin_match", 8), S("gloss_match", 8), S("lookalike", 6),
        S("word_meaning_mcq", 6), S("cloze", 6), S("passage_read", 5),
        S("word_search", 8), S("code_breaker"),
    ],
    "classroom": [
        S("minimal_pairs", 12), S("pinyin_partial", 12),
        S("use_the_word", 6), S("measure_word", 11),
    ],
    "classroom_lite": [
        S("minimal_pairs", 8), S("pinyin_partial", 8), S("measure_word", 8),
    ],
    "starter": [
        S("pinyin_write", 10), S("pinyin_partial", 10), S("lookalike", 6),
        S("cloze", 5),
    ],
    "bingo": [S("bingo_card")],
}

# "auto" = try everything in a sensible order; whatever has no material is dropped
PRESETS["auto"] = PRESETS["full"]


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

DEFAULT_ALLOW = ("verified", "authored", "open")

# Ordered warm-up -> production. Each entry caps how many items that type may
# contribute to one sheet, so no single drill dominates a 45-minute lesson.
# The tail (PRODUCTION) gets a reserved share of the budget, otherwise fast
# recognition drills fill the whole lesson and nothing gets written.
DRILL_PLAN = [
    ("minimal_pairs",   16),
    ("pinyin_partial",  16),
    ("pinyin_write",    12),
    ("lookalike",       10),
    ("pinyin_match",     8),
    ("tone_mark",       10),
    ("gloss_match",      8),
    ("antonym",          8),
    ("make_words",       8),
    ("measure_word",    12),
    ("homophone",        6),
    ("word_meaning_mcq", 6),
    ("pinyin_read",      8),
    ("word_search",      8),
]

PRODUCTION_PLAN = [
    ("cloze",           10),
    ("scramble",         5),
    ("passage_read",     6),
    ("use_the_word",     6),
    ("pattern_write",    3),
]


def _probe(scope, tid, count, seed, allow):
    """Generate one candidate section and report why if it did not survive."""
    qs, skipped, _ = generate(scope, [{"type": tid, "count": count}], seed,
                              allow=allow)
    if qs:
        return qs[0], ""
    reason = skipped[0] if skipped else "no material"
    return None, reason[len(tid) + 2:-1] if reason.startswith(tid + " (") else reason


def plan_for_minutes(scope, seed: int, target: float, allow: tuple,
                     production_share: float = 0.3, tolerance: float = 2.5):
    """Fill a lesson to a target duration using real generated output.

    Nothing is estimated from an unbuilt section: every candidate is generated,
    measured, and only then accepted, trimmed or dropped. The tail of the sheet
    is reserved for production work so a lesson never ends up as pure recognition.
    """
    settling = qbank.TIMING_META["settling"]
    sections, total, log = [], settling, []
    prod_budget = target * production_share
    total, sections, log = _fill(scope, seed, target - prod_budget, allow,
                                 DRILL_PLAN, total, sections, log, tolerance)
    total, sections, log = _fill(scope, seed, target, allow,
                                 PRODUCTION_PLAN, total, sections, log, tolerance)
    # anything left over goes back to recognition drills that were skipped
    total, sections, log = _fill(scope, seed, target, allow, DRILL_PLAN,
                                 total, sections, log, tolerance,
                                 exclude={s["type"] for s in sections})
    return sections, total, log


def _fill(scope, seed, target, allow, plan, total, sections, log, tolerance,
          exclude=frozenset()):
    overhead = qbank.TIMING_META["overhead"] / 60.0
    for tid, cap in plan:
        if tid in exclude or any(s["type"] == tid for s in sections):
            continue
        if total >= target - tolerance:
            break
        q, why = _probe(scope, tid, cap, seed, allow)
        if q is None:
            log.append(f"{tid}: SKIPPED — {why}")
            continue
        per = (q.est_minutes - overhead) / max(1, q.items_n)
        room = target - total
        if q.est_minutes <= room + tolerance:
            sections.append({"type": tid, "count": cap})
            total += q.est_minutes
            log.append(f"{tid}: +{q.items_n} items, {q.est_minutes:.1f} min")
            continue
        fit = int((room - overhead) / per) if per > 0 else 0
        if fit >= 3:                       # a section under 3 items is not worth a heading
            q2, _ = _probe(scope, tid, fit, seed, allow)
            if q2 is not None:
                sections.append({"type": tid, "count": fit})
                total += q2.est_minutes
                log.append(f"{tid}: +{q2.items_n} items (trimmed to fit), "
                           f"{q2.est_minutes:.1f} min")
    return total, sections, log


def generate(scope: Scope, sections: List[dict], seed: int,
             attempts: int = 6, allow: tuple = DEFAULT_ALLOW) -> tuple:
    questions: List[Question] = []
    skipped: List[str] = []
    rejected: Dict[str, list] = {}
    for i, sec in enumerate(sections):
        t = sec["type"]
        if t == "heading":
            questions.append(Question(
                type_id="heading", title_zh=sec.get("zh", ""),
                title_en="  " + sec.get("en", ""), body_html="",
                answer_html="", marks=0, est_minutes=0))
            continue
        spec = REGISTRY.get(t)
        if not spec:
            skipped.append(f"{t} (unknown type)")
            continue
        if spec.confidence not in allow:
            skipped.append(f"{t} (confidence '{spec.confidence}' not enabled — "
                           f"{spec.risk or 'see --audit'})")
            continue
        q, why = None, []
        for attempt in range(attempts):
            ctx = Ctx(scope=scope,
                      rng=random.Random(f"{seed}:{t}:{i}:{attempt}"),
                      params=sec.get("params", {}),
                      count=sec.get("count", spec.default_count))
            try:
                cand = spec.fn(ctx)
            except Exception as e:                               # noqa: BLE001
                why = [f"error: {e}"]
                break
            if cand is None:
                why = ["not enough material in scope"]
                break
            prov = cand.meta.get("provenance")
            if prov == "derived" and "derived" not in allow:
                why = ["only auto-enriched data available for this lesson"]
                break
            issues = validate.validate(cand, ctx)
            if not issues:
                q = cand
                break
            why = [str(x) for x in issues]
        if q is not None:
            n = q.items_n or 1
            q.est_minutes = (qbank.seconds_per_item(t, spec.minutes_each) * n
                             + qbank.TIMING_META["overhead"]) / 60.0
        if q is None:
            skipped.append(f"{t} ({why[0] if why else 'failed validation'})")
            if why:
                rejected[t] = why
            continue
        questions.append(q)
    return questions, skipped, rejected


CATEGORY_HEADING = {
    "form": ("字", "Characters"), "sound": ("音", "Pinyin"),
    "meaning": ("词", "Vocabulary"), "sentence": ("句", "Sentences"),
    "reading": ("阅读", "Reading"), "puzzle": ("玩一玩", "Puzzle"),
    "production": ("写一写", "Write"),
}
CATEGORY_ORDER = ["form", "sound", "meaning", "sentence", "reading",
                  "puzzle", "production"]


def _group_by_category(sections: List[dict]) -> List[dict]:
    """Group a flat, duration-planned section list under the same 一、字 /
    二、音 / ... headings a hand-pinned recipe uses, so a `minutes:`-planned
    recipe still reads like an organized worksheet instead of a flat list."""
    by_cat: Dict[str, List[dict]] = {}
    for sec in sections:
        by_cat.setdefault(REGISTRY[sec["type"]].category, []).append(sec)
    out, n = [], 0
    for cat in CATEGORY_ORDER:
        secs = by_cat.get(cat)
        if not secs:
            continue
        n += 1
        zh, en = CATEGORY_HEADING[cat]
        out.append({"type": "heading", "zh": f"{cn_num(n)}、{zh}", "en": en})
        out.extend(secs)
    return out


def _annotate_minutes(rep: dict, target: float, plan_log: list) -> None:
    """Attach the same target/shortfall reporting whether the plan came from
    --minutes (corpus mode) or a recipe's `minutes:` field."""
    settle = qbank.TIMING_META["settling"]
    rep["target_minutes"] = target
    rep["settling_allowance"] = settle
    rep["lesson_minutes"] = round(rep["minutes"] + settle)
    short = target - rep["lesson_minutes"]
    rep["plan"] = plan_log
    if short > 3:
        rep["shortfall"] = (
            f"{short:.0f} min short of target — the scope ran out of "
            f"material. Widen it (more lessons/review), or author cloze / "
            f"truefalse / comprehension items for these lessons.")


def qa_report(scope: Scope, questions: List[Question]) -> Dict[str, list]:
    """Closed-vocabulary gate: flag any Hanzi a student has not been taught."""
    leaks, advisories = {}, {}
    for i, q in enumerate(questions, 1):
        bad = scope.leaks(q.student_hanzi)
        if not bad:
            continue
        (advisories if q.leak_mode == "advisory" else leaks)[f"{i}. {q.type_id}"] = sorted(bad)
    return {"leaks": leaks, "advisories": advisories}


# --------------------------------------------------------------------------
# Build one worksheet
# --------------------------------------------------------------------------

def build_one(*, corpus: Optional[Corpus], book: int, lessons: List[int],
              sections: List[dict], seed: int, out: Path, recipe_id: str,
              vocabulary: str = "cumulative", title: Optional[str] = None,
              density: str = "", show_key: bool = True,
              school_line: str = "本校 · 内部使用 Internal use",
              ad_hoc: Optional[Lesson] = None, strict: bool = False,
              style: str = "workbook", lang: str = "both",
              allow: tuple = DEFAULT_ALLOW, show_marks: bool = False,
              review: Optional[dict] = None) -> dict:
    if ad_hoc is not None:
        scope = Scope([ad_hoc], [ad_hoc], ad_hoc.title)
        subtitle = ad_hoc.title
        head = title or "中文练习 Chinese Practice"
    else:
        scope = Scope.build(corpus, book, lessons, vocabulary, review=review, seed=seed)
        first = scope.target_lessons[0]
        head = title or (f"《中文》第{cn_num(book)}册　第"
                         + "、".join(cn_num(l) for l in lessons) + "课　练习")
        subtitle = " / ".join(l.title for l in scope.target_lessons if l.title)
        subtitle = subtitle or "Jinan University 《中文》 series"

    questions, skipped, rejected = generate(scope, sections, seed,
                                           allow=allow)
    real = [q for q in questions if q.type_id != "heading"]
    qa = qa_report(scope, real)
    leaks, advisories = qa["leaks"], qa["advisories"]

    scope_label = scope.label
    review_note = ""
    review_chars = scope.review_chars()
    if review_chars:
        books_used = sorted({l.book for l in scope.review_lessons})
        review_note = (f" · 复习字（第{'、'.join(cn_num(b) for b in books_used)}册）"
                       f"{len(review_chars)} 个")
    teacher_note = (f"生字 {len(scope.target_chars())} 个 · "
                    f"词语 {len(scope.target_words())} 个 · "
                    f"已学字库 {len(scope.allowed_charset())} 字{review_note}")

    html = render_worksheet(
        title=head, subtitle=subtitle, scope_label=scope_label,
        questions=questions, seed=seed, recipe_id=recipe_id,
        density=density, show_key=show_key, school_line=school_line,
        style=style, lang=lang, show_marks=show_marks, teacher_note=teacher_note,
        footer_note=("closed-vocabulary + key uniqueness checked" if not leaks
                     else "⚠ vocabulary leak — see build log"),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    report = {"file": str(out), "questions": len(real),
              "marks": sum(q.marks for q in real),
              "items": sum(q.items_n for q in real),
              "minutes": round(sum(q.est_minutes for q in real)),
              "est_pages": _est_pages(real, density, style),
              "page_warning": _page_warning(_est_pages(real, density, style)),
              "skipped": skipped, "rejected_for_ambiguity": rejected,
              "leaks": leaks, "advisories": advisories}
    if review_chars:
        report["review"] = {
            "books": sorted({l.book for l in scope.review_lessons}),
            "count": len(review_chars),
            "chars": [c.char for c in review_chars],
        }
    elif review and review.get("books"):
        report["review"] = {"books": review["books"], "count": 0,
                            "note": "no lessons found for those book numbers "
                                    "in the loaded data — check --data covers them"}
    if strict and leaks:
        raise SystemExit(f"STRICT: vocabulary leak in {out}: {leaks}")
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

# Calibrated against real Chromium A4 renders (see tools/calibrate.py).
_ROWS_PER_PAGE = {"": 20.9, "compact": 24.5, "spacious": 17.0}


def _est_pages(questions, density: str, style: str) -> float:
    """Rough print-length estimate so a sheet does not spill onto a stray page."""
    rows = 3.0
    for q in questions:
        rows += 2.2 + (0.6 if q.instruction_zh else 0)
        b = q.body_html
        rows += b.count("tzg-row") * 3.4
        rows += b.count("<tr") * 1.1
        rows += b.count("wline") * 1.0
        rows += b.count('class="item') * (0.5 if 'items c3' in b or 'items c4' in b else 1.0)
        rows += b.count('class="pair"') * 1.0
        rows += b.count('class="cell"') * 0.7
        rows += 1.5 if "bank" in b else 0
    per = _ROWS_PER_PAGE.get(density, 46.0) * (1.06 if style == "drill" else 1.0)
    return round(rows / per, 2)


def _page_warning(est: float) -> str:
    """Flag a sheet that barely spills onto another sheet of paper."""
    frac = est - int(est)
    if est > 1 and 0 < frac <= 0.25:
        return (f"~{est} pages: the last page is only {int(frac*100)}% used. "
                f"Try --density compact, or drop one section.")
    if est > 1 and frac >= 0.85:
        return f"~{est} pages: very close to spilling. Check the print preview."
    return ""


def load_corpus(data) -> Corpus:
    """`data` is a single path, a comma-separated string of paths (CLI), or a
    YAML list of paths (recipe `data:` field) — load_many merges books so a
    Scope can pull review characters from an earlier book's file."""
    paths = [p.strip() for p in data.split(",") if p.strip()] \
        if isinstance(data, str) else list(data)
    return Corpus.load_many(paths) if len(paths) > 1 else Corpus.load(paths[0])


def load_recipe(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise SystemExit("pyyaml not installed: pip install pyyaml")
        return yaml.safe_load(text)
    return json.loads(text)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="zhw.build")
    ap.add_argument("--data", default="data/zhongwen.json",
                    help="one path, or several comma-separated paths merged "
                         "into one corpus (e.g. data/book9.json,data/book7.json,"
                         "data/book8.json) — needed for --review-books to reach "
                         "another book's file")
    ap.add_argument("--recipe")
    ap.add_argument("--book", type=int)
    ap.add_argument("--lesson", type=int, action="append")
    ap.add_argument("--all", action="store_true", help="every lesson in the book")
    ap.add_argument("--preset", default="classroom", choices=sorted(PRESETS))
    ap.add_argument("--production-share", type=float, default=0.3,
                    help="fraction of the lesson reserved for writing/production")
    ap.add_argument("--minutes", type=float,
                    help="target lesson length; builds the sheet to fit and "
                         "reports what it actually achieved")
    ap.add_argument("--types", help="comma-separated type ids, overrides preset")
    ap.add_argument("--chars", help="feed characters directly, e.g. 店区近边")
    ap.add_argument("--words", default="")
    ap.add_argument("--sentences", default="")
    ap.add_argument("--vocabulary", default="cumulative",
                    choices=["lesson", "book", "cumulative"])
    ap.add_argument("--review-books",
                    help="comma-separated earlier book numbers to draw review "
                         "characters from, e.g. 7,8 — mixed into every "
                         "character-based question type, not just distractors, "
                         "so a sheet is not 100%% brand-new material a student "
                         "may have forgotten or not reached yet")
    ap.add_argument("--review-ratio", type=float, default=0.0,
                    help="fraction of the character-drill pool made up of "
                         "review characters, e.g. 0.3 (with --review-books)")
    ap.add_argument("--review-count", type=int,
                    help="fixed number of review characters instead of a ratio")
    ap.add_argument("--review-tier", default="write", choices=["write", "read"],
                    help="tier of review characters to mix in (default write)")
    ap.add_argument("--seed", type=int, default=20260726)
    ap.add_argument("--density", default="", choices=["", "compact", "spacious"])
    ap.add_argument("--style", default="drill", choices=["drill", "workbook"],
                    help="drill = dense classroom layout (default); workbook = "
                         "scaffolded, wide-spaced")
    ap.add_argument("--lang", default="both", choices=["both", "zh", "en"])
    ap.add_argument("--no-key", action="store_true")
    ap.add_argument("--marks", action="store_true",
                    help="print mark tallies and a score field — for an actual "
                         "assessment, not a classroom exercise sheet")
    ap.add_argument("--strict", action="store_true",
                    help="fail the build on any out-of-scope character")
    ap.add_argument("--out", default="out")
    ap.add_argument("--title")
    ap.add_argument("--list-types", action="store_true")
    ap.add_argument("--audit", action="store_true",
                    help="print every type with its correctness classification")
    ap.add_argument("--allow", default="verified,authored,open",
                    help="confidence tiers to enable; add 'derived' at your own risk")
    a = ap.parse_args(argv)

    allow = tuple(x.strip() for x in a.allow.split(",") if x.strip())
    review = None
    if a.review_books:
        review = {"books": [int(x) for x in a.review_books.split(",") if x.strip()],
                  "ratio": a.review_ratio, "count": a.review_count,
                  "tier": a.review_tier}

    if a.audit:
        by = {}
        for t in REGISTRY.values():
            by.setdefault(t.confidence, []).append(t)
        for tier in ("verified", "authored", "open", "derived"):
            ts = sorted(by.get(tier, []), key=lambda t: t.id)
            if not ts:
                continue
            on = "ENABLED " if tier in allow else "DISABLED"
            print(f"\n=== {tier.upper()} ({on}) — {qbank.CONFIDENCE[tier]} ===")
            for t in ts:
                print(f"  {t.id:<16} {t.name_zh}")
                if t.risk:
                    print(f"      risk: {t.risk}")
        print(f"\n{len(REGISTRY)} types; "
              f"{sum(1 for t in REGISTRY.values() if t.confidence in allow)} enabled.")
        return 0

    if a.list_types:
        for cat, label in qbank.CATEGORIES.items():
            ts = types_by_category().get(cat, [])
            if not ts:
                continue
            print(f"\n{label}")
            for t in ts:
                mark = "" if t.confidence in allow else "  [off: %s]" % t.confidence
                print(f"  {t.id:<18} {t.name_zh:<10} {t.name_en}{mark}")
        print(f"\n{len(REGISTRY)} question types registered.")
        return 0

    sections = ([{"type": t.strip()} for t in a.types.split(",")]
                if a.types else PRESETS[a.preset])

    # --- ad-hoc mode -----------------------------------------------------
    if a.chars:
        ls = ad_hoc_lesson(a.chars, a.words, a.sentences)
        for c in ls.chars:
            enrich.enrich_char(c)
        for w in ls.words:
            w.pinyin = w.pinyin or enrich.auto_pinyin(w.word)
        rep = build_one(corpus=None, book=0, lessons=[0], sections=sections,
                        seed=a.seed, out=Path(a.out) / "adhoc.html",
                        recipe_id=f"adhoc/{a.preset}", title=a.title,
                        density=a.density, show_key=not a.no_key,
                        ad_hoc=ls, strict=a.strict, style=a.style, lang=a.lang, allow=allow,
                        show_marks=a.marks)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    # --- recipe mode -----------------------------------------------------
    if a.recipe:
        r = load_recipe(Path(a.recipe))
        corpus = load_corpus(r.get("data", a.data))
        enrich.enrich_corpus(corpus)
        sc = r["scope"]
        lay = r.get("layout", {})
        seed = r.get("seed", a.seed)
        r_allow = tuple(r.get("allow", allow))
        r_review = sc.get("review", review)
        sections, plan_log = r.get("sections"), None
        if sections is None:
            if "minutes" not in r:
                raise SystemExit(f"recipe {r['id']}: needs 'sections:' or 'minutes:'")
            probe = Scope.build(corpus, sc["book"], sc["lessons"],
                                sc.get("vocabulary", "cumulative"),
                                review=r_review, seed=seed)
            sections, _, plan_log = plan_for_minutes(
                probe, seed, r["minutes"], r_allow,
                production_share=r.get("production_share", 0.3))
            sections = _group_by_category(sections)
        rep = build_one(
            corpus=corpus, book=sc["book"], lessons=sc["lessons"],
            sections=sections, seed=seed,
            out=Path(r.get("out", f"{a.out}/{r['id']}.html")),
            recipe_id=r["id"], vocabulary=sc.get("vocabulary", "cumulative"),
            title=r.get("title"), density=lay.get("density", ""),
            show_key=lay.get("answer_key", True),
            school_line=lay.get("school_line", "本校 · 内部使用 Internal use"),
            strict=r.get("strict", a.strict),
            style=lay.get("style", a.style), lang=lay.get("lang", a.lang),
            allow=r_allow,
            show_marks=lay.get("marks", a.marks),
            review=r_review)
        if plan_log is not None:
            _annotate_minutes(rep, r["minutes"], plan_log)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    # --- corpus mode -----------------------------------------------------
    corpus = load_corpus(a.data)
    enrich.enrich_corpus(corpus)
    if not a.book:
        raise SystemExit("--book required (or use --recipe / --chars)")
    targets = ([[l.lesson] for l in corpus.lessons_in(a.book)] if a.all
               else [a.lesson or [1]])
    reports = []
    for lessons in targets:
        secs, plan_log, achieved = sections, None, None
        if a.minutes:
            sc = Scope.build(corpus, a.book, lessons, a.vocabulary,
                             review=review, seed=a.seed)
            secs, achieved, plan_log = plan_for_minutes(
                sc, a.seed, a.minutes, allow,
                production_share=a.production_share)
        rid = (f"b{a.book}l{'-'.join(map(str, lessons))}-"
               f"{str(int(a.minutes)) + 'min' if a.minutes else a.preset}")
        rep = build_one(
            corpus=corpus, book=a.book, lessons=lessons, sections=secs,
            seed=a.seed, out=Path(a.out) / f"{rid}.html", recipe_id=rid,
            vocabulary=a.vocabulary, title=a.title, density=a.density,
            show_key=not a.no_key, strict=a.strict,
            style=a.style, lang=a.lang, allow=allow, show_marks=a.marks,
            review=review)
        if a.minutes:
            _annotate_minutes(rep, a.minutes, plan_log)
        reports.append(rep)
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
