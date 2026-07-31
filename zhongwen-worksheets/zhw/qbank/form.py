"""字形 — character form question types."""

from __future__ import annotations

from typing import Optional

from .. import enrich
from ..render import (Question, tzg_row, tianzige, stroke_sequence,
                      stroke_order_svg, blank, bracket, slot_marker, esc)
from . import register, Ctx


@register("trace", "描红写字", "Trace and write", "form",
          needs=("chars",), default_count=6, marks_each=1, minutes_each=1.0,
          confidence="open",
          blurb="田字格 tracing rows. The stroke-order strip is OFF by default: "
                "the stroke data is derived, not textbook-authoritative.")
def trace(ctx: Ctx) -> Optional[Question]:
    chars = ctx.pick(ctx.write_chars(), ctx.count)
    if not chars:
        return None
    boxes = ctx.p("boxes", 6)
    faded = ctx.p("faded", 2)
    grid = ctx.p("grid", "tian")
    show_order = ctx.p("stroke_order", False)   # derived data — opt in
    rows = []
    for c in chars:
        strip = (f'<div class="hint">笔顺 {stroke_sequence(c.char, 26)}　'
                 f'{c.stroke_count or "?"} 画</div>') if show_order else ""
        rows.append(f'<div style="margin-bottom:2mm">{strip}'
                    f'{tzg_row(c.char, boxes=boxes, models=1, faded=faded, grid=grid, pinyin=c.pinyin)}'
                    f'</div>')
    return Question(
        type_id="trace", title_zh="描红写字", title_en="Trace and write",
        instruction_zh="按笔顺描红，然后自己写。",
        instruction_en="Trace the faded characters following the stroke order, then write your own.",
        body_html="".join(rows),
        answer_html="书写练习，按笔顺与结构评分。 Handwriting task — mark on stroke order, proportion and 田字格 placement.",
        student_hanzi="".join(c.char for c in chars), answer_mode="open",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=1.0 * len(chars),
    )


@register("stroke_count", "数一数，写笔画数", "Count the strokes", "form",
          needs=("chars",), default_count=8, minutes_each=0.3,
          confidence="verified",
          risk="Splits slots between new-lesson and review characters in the "
               "same proportion as the sheet's overall practice pool (so one "
               "side having more teacher-verified counts on hand can't crowd "
               "the other out entirely), preferring teacher-supplied counts "
               "within each side. Falls back to enrichment (makemeahanzi) "
               "counts only when a side has none of its own, which marks the "
               "whole question derived and drops it unless --allow derived.")
def stroke_count(ctx: Ctx) -> Optional[Question]:
    pool = [c for c in ctx.chars() if c.stroke_count]
    if not pool:
        return None
    new_set = {c.char for c in ctx.scope.target_chars()}
    new_pool = [c for c in pool if c.char in new_set]
    review_pool = [c for c in pool if c.char not in new_set]

    def take(seq, n):
        teacher = [c for c in seq if "stroke_count" not in getattr(c, "derived", set())]
        derived = [c for c in seq if c not in teacher]
        picked = ctx.pick(teacher, min(n, len(teacher)))
        picked += ctx.pick(derived, min(n - len(picked), len(derived)))
        return picked

    total = len(ctx.scope.practice_chars()) or 1
    new_n = round(ctx.count * len(ctx.scope.target_chars()) / total)
    chosen = take(new_pool, new_n) + take(review_pool, ctx.count - new_n)
    if len(chosen) < ctx.count:                       # one side came up short
        leftover = [c for c in new_pool + review_pool if c not in chosen]
        chosen += take(leftover, ctx.count - len(chosen))
    chars = ctx.shuffled(chosen)
    if not chars:
        return None
    prov = ("derived" if any("stroke_count" in getattr(c, "derived", set())
                             for c in chars) else "teacher")
    items = "".join(
        f'<div class="item"><span class="lbl">({i})</span>'
        f'<span class="zh big">{esc(c.char)}</span>{blank("2.5em")}画</div>'
        for i, c in enumerate(chars, 1))
    ans = "　".join(f'({i}) {c.char}={c.stroke_count}' for i, c in enumerate(chars, 1))
    sol = [(c.char, str(c.stroke_count)) for c in chars]
    return Question(
        type_id="stroke_count", title_zh="数一数，写笔画数", title_en="Count the strokes",
        instruction_zh="数出每个字有几画，写在横线上。",
        instruction_en="Count the strokes in each character and write the number.",
        body_html=f'<div class="items c4">{items}</div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=sol, answer_mode="unique", meta={"provenance": prov},
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.3 * len(chars),
    )


@register("stroke_order", "按笔顺一笔一笔写", "Stroke order", "form",
          needs=("chars",), default_count=4, minutes_each=1.0,
          confidence="derived",
          risk="The marked answer is makemeahanzi's stroke order, which is not guaranteed to match the PRC 笔顺规范 taught in class.")
def stroke_order(ctx: Ctx) -> Optional[Question]:
    chars = [c for c in ctx.pick(ctx.chars(), ctx.count) if enrich.strokes(c.char)]
    if not chars:
        return None
    rows = []
    for c in chars:
        n = len(enrich.strokes(c.char))
        empties = "".join(f'<span class="so-cell">'
                          f'<span style="display:inline-block;width:26px;height:26px"></span>'
                          f'</span>' for _ in range(n))
        rows.append(f'<div class="item" style="align-items:center;margin-bottom:2mm">'
                    f'<span class="zh big" style="min-width:12mm">{esc(c.char)}</span>'
                    f'<span class="so-strip">{empties}</span></div>')
    ans = "".join(f'<div>{esc(c.char)} {stroke_sequence(c.char, 22)}</div>' for c in chars)
    _sol = [(c.char, str(c.stroke_count)) for c in chars]
    return Question(
        type_id="stroke_order", title_zh="按笔顺一笔一笔写", title_en="Write the stroke order",
        instruction_zh="在方格里一笔一笔地写出这个字。",
        instruction_en="Build each character one stroke at a time, in order.",
        body_html="".join(rows), answer_html=ans,
        student_hanzi="".join(c.char for c in chars),
        solution=_sol, answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=1.0 * len(chars),
    )


@register("radical_id", "写出部首", "Identify the radical", "form",
          needs=("chars",), default_count=8, minutes_each=0.3,
          confidence="derived",
          risk='makemeahanzi gives the Kangxi radical. Dictionaries and 《中文》 disagree on the 部首 of many characters (和, 相, 期...), so the key is arguable. Supply `radical` in the lesson data to make this dependable.')
def radical_id(ctx: Ctx) -> Optional[Question]:
    chars = [c for c in ctx.pick(ctx.chars(), ctx.count) if c.radical and c.radical != c.char]
    if len(chars) < 2:
        return None
    items = "".join(
        f'<div class="item"><span class="lbl">({i})</span>'
        f'<span class="zh big">{esc(c.char)}</span>部首{blank("3em")}</div>'
        for i, c in enumerate(chars, 1))
    ans = "　".join(f'({i}) {c.char}→{c.radical}' for i, c in enumerate(chars, 1))
    return Question(
        type_id="radical_id", title_zh="写出部首", title_en="Write the radical",
        instruction_zh="写出下面每个字的部首。",
        instruction_en="Write the radical of each character.",
        body_html=f'<div class="items c3">{items}</div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=[(c.char, c.radical) for c in chars], answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.3 * len(chars),
    )


@register("radical_sort", "按部首分类", "Sort by radical", "form",
          needs=("chars",), default_count=9, minutes_each=0.5,
          confidence="derived",
          risk='Same radical-source disagreement, compounded by having to bucket cleanly.')
def radical_sort(ctx: Ctx) -> Optional[Question]:
    pool = [c for c in ctx.all_chars() if c.radical and c.radical != c.char]
    groups = {}
    for c in pool:
        groups.setdefault(c.radical, [])
        if c.char not in [x.char for x in groups[c.radical]]:
            groups[c.radical].append(c)
    usable = {r: v for r, v in groups.items() if len(v) >= 2}
    if len(usable) < 2:
        return None
    picked = dict(list(ctx.shuffled(list(usable.items())))[:3])
    chars = [c for v in picked.values() for c in v][:ctx.count]
    chars = ctx.shuffled(chars)
    from ..render import wordbank
    bank = wordbank([c.char for c in chars], "汉字库", "Characters")
    cols = "".join(
        f'<div><div style="font-weight:700" class="zh">{esc(r)}</div>'
        f'<div style="border:.9pt solid #4a4a4a;min-height:20mm;padding:2mm"></div></div>'
        for r in picked)
    ans = "　".join(
        f'{r}: ' + "、".join(c.char for c in chars if c.radical == r) for r in picked)
    return Question(
        type_id="radical_sort", title_zh="按部首分类", title_en="Sort by radical",
        instruction_zh="把上面的字按部首写进相应的格子里。",
        instruction_en="Sort the characters into the correct radical boxes.",
        body_html=bank + f'<div class="items c3" style="margin-top:2mm">{cols}</div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=[(c.char, c.radical) for c in chars], answer_mode="unique",
        meta={"buckets": list(picked), "chars": [c.char for c in chars]},
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.5 * len(chars),
    )


@register("component_build", "部件组字", "Build from components", "form",
          needs=("chars",), default_count=6, minutes_each=0.4,
          confidence="derived",
          risk='IDS decomposition yields non-characters (亅, 卜, ？) and splits that are not how the character is taught.')
def component_build(ctx: Ctx) -> Optional[Question]:
    chars = [c for c in ctx.pick(ctx.chars(), ctx.count * 2)
             if len(c.components) >= 2][:ctx.count]
    if len(chars) < 2:
        return None
    items = "".join(
        f'<div class="item"><span class="lbl">({i})</span>'
        f'<span class="zh" style="font-size:13pt">'
        f'{" ＋ ".join(esc(x) for x in c.components[:3])}</span>'
        f'　→　{tianzige("", size="sm")}</div>'
        for i, c in enumerate(chars, 1))
    ans = "　".join(f'({i}) {c.char}' for i, c in enumerate(chars, 1))
    return Question(
        type_id="component_build", title_zh="部件组字", title_en="Build the character",
        instruction_zh="把部件合起来，写出一个字。",
        instruction_en="Combine the components and write the character.",
        body_html=f'<div class="items c2">{items}</div>',
        answer_html=ans, student_hanzi="".join("".join(c.components) for c in chars),
        solution=[(" + ".join(c.components[:3]), c.char) for c in chars],
        answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.4 * len(chars), leak_mode="advisory",
        notes="Components come from the makemeahanzi IDS decomposition; check each one reads naturally before printing.",
    )


@register("lookalike", "选字组词", "Choose the character that completes the word", "form",
          needs=("words",), default_count=6, minutes_each=0.4)
def lookalike(ctx: Ctx) -> Optional[Question]:
    pool = [c.char for c in ctx.all_chars()]
    words = [w for w in ctx.words() if len(w.word) >= 2]
    if not words:
        return None
    vocab = {x.word for x in ctx.all_words()}
    rows, keys, hz, sol, dw = [], [], [], [], []
    for w in ctx.pick(words, ctx.count):
        target, rest = w.word[0], w.word[1:]
        cand = enrich.nearest_lookalikes(target, pool, 5) or ctx.distractors([target], 4)
        alts = [a for a in cand if (a + rest) not in vocab][:2]
        if len(alts) < 2:
            continue
        i = len(rows) + 1
        dw += [a + rest for a in alts]
        opts = ctx.shuffled([target] + alts)
        labels = "ABCD"
        opt_html = "　".join(
            f'<span class="opt">{labels[j]}. <span class="zh big">{esc(o)}</span></span>'
            for j, o in enumerate(opts))
        rows.append(f'<div class="item" style="display:block;margin-bottom:1.5mm">'
                    f'<span class="lbl">({i})</span> '
                    f'{slot_marker()}<span class="zh big">{esc(rest)}</span>'
                    f'<span class="opts" style="display:inline-flex">{opt_html}</span></div>')
        keys.append(f'({i}) {labels[opts.index(target)]} {w.word}')
        sol.append((rest, target))
        hz.append("".join(opts) + w.word)
    if not rows:
        return None
    return Question(
        type_id="lookalike", title_zh="选字组词",
        title_en="Choose the character that completes the word",
        instruction_zh="□处缺一个字，字形相近的选项里只有一个能跟旁边的字组成学过的词语，圈出那个字母。",
        instruction_en="The □ shows a missing character. Only one of the similar-looking "
                       "options completes a word you have learned — circle that letter.",
        body_html="".join(rows), answer_html="　".join(keys),
        student_hanzi="".join(hz), solution=sol, answer_mode="unique",
        meta={"distractor_words": dw},
        marks=len(rows), marks_each=1, items_n=len(rows),
        est_minutes=0.4 * len(rows),
    )
