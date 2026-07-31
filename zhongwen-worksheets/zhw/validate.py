"""
Solvability validation — the answer to "matching and grouping questions come out
wrong because of the internal link, not the content".

A generated question is only accepted if its key is PROVABLY the only key.
Every question declares a machine-readable solution and an answer mode:

    answer_mode = "bijection"  items are matched from a shared pool (连线, single-use
                               banks, sorting) -> the link must be one-to-one
    answer_mode = "unique"     independent items, each with one right answer
    answer_mode = "open"       many answers are correct -> the key lists examples
    answer_mode = "teacher"    needs human judgement -> REJECTED, never printed

Generic checks
  * no empty answer, no duplicate prompt, no distractor that is also an answer
  * bijection only: no duplicate answer, no answer contained in another answer
    <- this is what kills ambiguous 连线 / 同音 / 同义 links

Type-specific checks are registered with @checker and run on top.

If a question fails, the builder re-rolls it with a fresh sub-seed up to
`attempts` times, then drops it and says why. Nothing ambiguous reaches print.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

CHECKERS: Dict[str, Callable] = {}


def checker(type_id: str):
    def deco(fn):
        CHECKERS[type_id] = fn
        return fn
    return deco


@dataclass
class Issue:
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.detail}"


# --------------------------------------------------------------------------
# Generic
# --------------------------------------------------------------------------

def generic_issues(q) -> List[Issue]:
    out: List[Issue] = _claim_checks(q)   # applies regardless of answer_mode
    if q.answer_mode == "teacher":
        return out + [Issue("needs-human-judgement",
                      "no machine-checkable key; type must supply category data")]
    if q.answer_mode == "open":
        return out
    if not q.solution:
        return out + [Issue("no-key", "checkable question declared no solution pairs")]

    prompts = [str(p) for p, _ in q.solution]
    answers = [str(a) for _, a in q.solution]

    if any(not a.strip() for a in answers):
        out.append(Issue("empty-answer", "a solution pair has a blank answer"))

    dup_p = _dups(prompts)
    if dup_p:
        out.append(Issue("duplicate-prompt",
                         f"the same prompt appears twice: {dup_p}"))

    if q.answer_mode == "bijection":
        dup_a = _dups(answers)
        if dup_a:
            out.append(Issue("ambiguous-link",
                             f"two items share an answer, so the match is not "
                             f"one-to-one: {dup_a}"))
        for i, a in enumerate(answers):
            for j, b in enumerate(answers):
                if i != j and a != b and (a.startswith(b) or a.endswith(b)):
                    out.append(Issue("overlapping-answer",
                                     f"'{b}' is contained in '{a}' — marking dispute"))
                    break

    bad = set(q.distractors) & set(answers)
    if bad:
        out.append(Issue("distractor-is-answer",
                         f"distractor is also a correct answer: {sorted(bad)}"))
    return out


# Phrases that promise something specific must be backed by that something.
# This is the systematic half of the fix for "照例子" being shown with no
# example present, and "比一比" being shown with nothing to compare — instead
# of patching each occurrence by hand, any type using these phrases is now
# checked at build time, so a future type can't reintroduce the same gap.
_CLAIM_MARKERS = {
    "照例子": ('class="hint"', "instruction promises a worked example (照例子) "
                              "but the body has no example marker"),
    "照样子": ('class="hint"', "instruction promises a model/pattern example (照样子) "
                              "but the body has no example marker"),
    "比一比": ("pair", "instruction says 'compare' (比一比) but the body has no "
                       "paired/contrasted layout"),
}


def _claim_checks(q) -> List[Issue]:
    out = []
    text = (q.instruction_zh or "") + (q.instruction_en or "")
    for phrase, (needle, msg) in _CLAIM_MARKERS.items():
        if phrase in text and needle not in q.body_html:
            out.append(Issue("unfulfilled-claim", msg))
    return out


def _dups(seq) -> List[str]:
    seen, dup = set(), set()
    for x in seq:
        (dup if x in seen else seen).add(x)
    return sorted(dup)


def validate(q, ctx=None) -> List[Issue]:
    issues = generic_issues(q)
    fn = CHECKERS.get(q.type_id)
    if fn:
        try:
            issues += fn(q, ctx) or []
        except Exception as e:                                   # noqa: BLE001
            issues.append(Issue("checker-error", str(e)))
    return issues


# --------------------------------------------------------------------------
# Type-specific
# --------------------------------------------------------------------------

@checker("word_search")
def _word_search(q, ctx) -> List[Issue]:
    """Padding must not accidentally spell a target word anywhere else."""
    grid: List[List[str]] = q.meta.get("grid") or []
    targets: List[str] = q.meta.get("targets") or []
    if not grid:
        return []
    lines = ["".join(r) for r in grid]
    lines += ["".join(grid[r][c] for r in range(len(grid))) for c in range(len(grid[0]))]
    out = []
    for w in targets:
        n = sum(line.count(w) for line in lines)
        if n > 1:
            out.append(Issue("duplicate-in-grid",
                             f"'{w}' can be found {n} times — the key is not unique"))
    return out


@checker("cloze")
def _cloze(q, ctx) -> List[Issue]:
    """Each removed word must fit exactly one gap, and only that gap."""
    gaps = q.meta.get("gaps") or []          # [(sentence_with_word, removed_word)]
    bank = q.meta.get("bank") or []
    out = []
    for sent, word in gaps:
        if sent.count(word) != 1:
            out.append(Issue("multi-occurrence",
                             f"'{word}' appears {sent.count(word)}x in its own sentence"))
        for other in bank:
            if other != word and other in sent:
                out.append(Issue("bank-word-in-sentence",
                                 f"bank word '{other}' already sits in the sentence "
                                 f"needing '{word}'"))
    for _, word in gaps:
        hits = [s for s, w in gaps if w != word and word in s]
        if hits:
            out.append(Issue("cross-gap-fit",
                             f"'{word}' would also fit another gap"))
    return out


@checker("lookalike")
def _lookalike(q, ctx) -> List[Issue]:
    """A distractor must not itself form a real word with the remaining chars."""
    if ctx is None:
        return []
    vocab = {w.word for w in ctx.all_words()}
    out = []
    for wrong_word in q.meta.get("distractor_words", []):
        if wrong_word in vocab:
            out.append(Issue("distractor-forms-word",
                             f"'{wrong_word}' is also a real word in scope"))
    return out


@checker("homophone")
def _homophone(q, ctx) -> List[Issue]:
    return _lookalike(q, ctx)


@checker("radical_sort")
def _radical_sort(q, ctx) -> List[Issue]:
    """A character must belong to exactly one of the offered buckets."""
    from . import enrich
    buckets = q.meta.get("buckets") or []
    out = []
    for ch in q.meta.get("chars") or []:
        fits = [b for b in buckets
                if enrich.radical(ch) == b or b in enrich.components(ch)]
        if len(fits) != 1:
            out.append(Issue("ambiguous-bucket",
                             f"'{ch}' could be argued into {fits or 'no bucket'}"))
    return out


@checker("measure_word")
def _measure_word(q, ctx) -> List[Issue]:
    """'Each word used once' must actually be true."""
    used = [a for _, a in q.solution]
    bank = q.meta.get("bank") or []
    out = []
    if sorted(used) != sorted(bank):
        out.append(Issue("bank-mismatch",
                         "the bank and the key are not a one-to-one match"))
    nouns = [p for p, _ in q.solution]
    for i, (n1, m1) in enumerate(q.solution):
        for n2, m2 in q.solution[i + 1:]:
            if m1 != m2 and _interchangeable(n1, m2, ctx) and _interchangeable(n2, m1, ctx):
                out.append(Issue("swappable-measures",
                                 f"{m1}/{m2} could be swapped between {n1}/{n2}"))
    return out


def _interchangeable(noun: str, measure: str, ctx) -> bool:
    if ctx is None:
        return False
    for ls in ctx.scope.allowed_lessons:
        for m, n in ls.measures:
            if n == noun and m == measure:
                return True
    return False


@checker("sentence_order")
def _sentence_order(q, ctx) -> List[Issue]:
    if not q.meta.get("from_passage"):
        return [Issue("no-canonical-order",
                      "sentences came from an unordered example list, so more "
                      "than one order is defensible — needs a real 课文 passage")]
    return []


@checker("pinyin_partial")
def _pinyin_partial(q, ctx) -> List[Issue]:
    """A gap must have exactly one in-scope character that fits its pinyin."""
    if ctx is None:
        return []
    from . import enrich
    vocab = {w.word for w in ctx.all_words()}
    pool = [c.char for c in ctx.all_chars()]
    out = []
    for word, _ in q.meta.get("items", []):
        for hide in (0, 1):
            target, shown = word[hide], word[1 - hide]
            py = ctx.pinyin_of(target)
            rivals = [c for c in pool if c != target and ctx.pinyin_of(c) == py
                      and ((c + shown) if hide == 0 else (shown + c)) in vocab]
            if rivals:
                out.append(Issue("two-characters-fit",
                                 f"'{py}' in {word} is also satisfied by {rivals}"))
    return out
