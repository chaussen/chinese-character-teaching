"""
Classroom drill types — dense, plain, fast to mark.

Modelled on the CFCS/CRAN Unit Test format: bracketed 形近字 pairs, pinyin
written above a gap inside a partial word, 造句 from an underlined word, and a
single-use 量词 bank. Minimal furniture, high item count per page.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .. import enrich
from ..render import Question, esc, bracket, writing_lines
from . import register, Ctx

PUNCT = "，。？！、；：“”‘’《》…—"


@register("minimal_pairs", "形近字组词", "Make a word for each similar character", "form",
          needs=("chars",), default_count=12, marks_each=1, minutes_each=0.35,
          confidence="open",
          blurb="Bracketed 形近字 pairs, each needing a word. Very high density.")
def minimal_pairs(ctx: Ctx) -> Optional[Question]:
    pool = [c.char for c in ctx.all_chars()]
    words = ctx.all_words()

    def words_for(ch):
        return [w.word for w in words if ch in w.word]

    min_score = ctx.p("min_score", 0.35)

    def genuinely_similar(a, b):
        """Reject weak pairs: a real 形近字 pair shares a component or radical."""
        if enrich.similarity(a, b) < min_score:
            return False
        shared = set(enrich.components(a)) & set(enrich.components(b))
        return bool(shared) or (enrich.radical(a) and
                                enrich.radical(a) == enrich.radical(b))

    pairs, used = [], set()
    for c in ctx.shuffled(ctx.chars()):
        if c.char in used or not words_for(c.char):
            continue
        mates = [m for m in enrich.nearest_lookalikes(c.char, pool, 8)
                 if genuinely_similar(c.char, m)]
        mate = next((m for m in mates if m not in used and words_for(m)), None)
        if not mate:
            continue
        pairs.append((c.char, mate))
        used.update({c.char, mate})
        if len(pairs) * 2 >= ctx.count:
            break
    if len(pairs) < 2:
        return None

    cells = []
    for a, b in pairs:
        cells.append(
            f'<div class="pair"><span class="brace">&#123;</span>'
            f'<span class="col">'
            f'<span class="row"><span class="zh">{esc(a)}</span>'
            f'{bracket(2.4)}</span>'
            f'<span class="row"><span class="zh">{esc(b)}</span>'
            f'{bracket(2.4)}</span>'
            f'</span></div>')

    sol, key = [], []
    for a, b in pairs:
        for ch in (a, b):
            ex = words_for(ch)[:3]
            sol.append((ch, ex[0] if ex else ""))
            key.append(f'{ch}（{"／".join(ex)}）')
    return Question(
        type_id="minimal_pairs",
        title_zh="形近字组词", title_en="Make a word for each similar character",
        instruction_zh="每组两个字长得很像，别弄混了。给每个字组一个学过的词，写在括号里。",
        instruction_en="Each pair looks similar — don't mix them up. Write one word "
                       "you've learned for each character in the brackets.",
        body_html=f'<div class="pairs">{"".join(cells)}</div>',
        answer_html="　".join(key),
        student_hanzi="".join(a + b for a, b in pairs),
        solution=sol, answer_mode="open",
        marks=len(pairs) * 2, marks_each=1, items_n=len(pairs) * 2,
        est_minutes=0.35 * len(pairs) * 2,
        notes="Accept any correct word containing the character — the listed ones "
              "are simply the in-scope examples.",
    )


@register("pinyin_partial", "根据拼音写出中文字词", "Write the missing character", "sound",
          needs=("words",), default_count=12, marks_each=1, minutes_each=0.4,
          blurb="Pinyin above a gap inside a partial word — the CRAN 第二题 format.")
def pinyin_partial(ctx: Ctx) -> Optional[Question]:
    words = [w for w in ctx.all_words() if len(w.word) == 2]
    words = ctx.pick(words, ctx.count)
    if len(words) < 3:
        return None

    cells, sol, key, hz = [], [], [], []
    for i, w in enumerate(words):
        hide = ctx.rng.randrange(2)
        target = w.word[hide]
        shown = w.word[1 - hide]
        py = ctx.pinyin_of(target)
        shown_slot = f'<span class="pyfill-slot"><span class="py"></span><span class="frag">{esc(shown)}</span></span>'
        gap_slot = f'<span class="pyfill-slot"><span class="py">{esc(py)}</span><span class="gap"></span></span>'
        slots = [gap_slot, shown_slot] if hide == 0 else [shown_slot, gap_slot]
        cells.append(f'<div class="cell">{"".join(slots)}</div>')
        sol.append((w.word.replace(target, "＿", 1) + f" [{py}]", target))
        key.append(f'{py} → {w.word}')
        hz.append(shown)
    return Question(
        type_id="pinyin_partial",
        title_zh="根据拼音写出中文字词", title_en="Write the missing character",
        instruction_zh="根据拼音，把缺的字写上。",
        instruction_en="Use the pinyin to write the missing character.",
        body_html=f'<div class="pyfill">{"".join(cells)}</div>',
        answer_html="　".join(key), student_hanzi="".join(hz),
        solution=sol, answer_mode="unique",
        meta={"items": [(w.word, ctx.pinyin_of(w.word[0])) for w in words]},
        marks=len(words), marks_each=1, items_n=len(words),
        est_minutes=0.4 * len(words),
    )


@register("use_the_word", "用划线的词写一句新句子", "Write a new sentence with the underlined word", "sentence",
          needs=("sentences",), default_count=6, marks_each=2, minutes_each=1.5,
          confidence="open",
          blurb="Textbook sentence with the target word underlined — the CRAN 第三题.")
def use_the_word(ctx: Ctx) -> Optional[Question]:
    sents = ctx.scope.target_sentences()
    targets = [w.word for w in ctx.words() if len(w.word) >= 2]
    targets += ctx.scope.target_patterns()
    if not sents:
        return None

    rows, sol, hz = [], [], []
    for s in ctx.shuffled(sents):
        hit = next((t for t in targets if t and t in s), None)
        if not hit:
            continue
        shown = s.replace(hit, f'<span class="uline">{esc(hit)}</span>', 1)
        rows.append(f'<div style="margin-bottom:1mm"><div class="item sent">'
                    f'<span class="lbl">{len(rows)+1}.</span>'
                    f'<span class="hint">例：</span>'
                    f'<span class="zh">{shown}</span></div>{writing_lines(1)}</div>')
        sol.append((hit, "open"))
        hz.append(s)
        if len(rows) >= ctx.count:
            break
    if not rows:
        return None
    return Question(
        type_id="use_the_word", title_zh="用划线的词写一句新句子",
        title_en="Write a new sentence with the underlined word",
        instruction_zh="每句话下面的划线词都配了一个例句。读一读例句，再用这个词写一句不同的新句子。",
        instruction_en="Each underlined word comes with an example sentence below it. "
                       "Read the example, then write your own different sentence using "
                       "the same word.",
        body_html="".join(rows),
        answer_html="自由作答。 Open. Mark 1 for correct use of the target word, "
                    "1 for a complete, punctuated sentence that is NOT a copy of the example.<br>"
                    + "　".join(esc(a) for a, _ in sol),
        student_hanzi="".join(hz), solution=sol, answer_mode="open",
        marks=len(rows) * 2, marks_each=2, items_n=len(rows),
        est_minutes=1.5 * len(rows),
    )


@register("measure_word", "量词", "Measure words", "sentence",
          needs=("measures",), default_count=11, marks_each=1, minutes_each=0.35,
          blurb="One shared bank, each measure word used exactly once.")
def measure_word(ctx: Ctx) -> Optional[Question]:
    raw = ctx.scope.target_measures() or [
        m for ls in ctx.scope.allowed_lessons for m in ls.measures]
    seen, pairs = set(), []
    for m, noun in raw:                      # one measure word, used once only
        if m in seen or noun in {n for _, n in pairs}:
            continue
        seen.add(m)
        pairs.append((m, noun))
    pairs = pairs[:ctx.count]
    if len(pairs) < 3:
        return None

    bank = ctx.shuffled([m for m, _ in pairs])
    numerals = ["一", "两", "三", "一", "两"]   # keep quantities plausible
    items = "".join(
        f'<div class="item"><span class="zh" style="font-size:12pt">'
        f'{numerals[ctx.rng.randrange(len(numerals))] if i else "一"}'
        f'{bracket(1.4)}{esc(noun)}</span></div>'
        for i, (m, noun) in enumerate(pairs))
    bank_html = ('<div class="bank"><span class="bank-t"></span>'
                 + "".join(f'<span class="chip zh">{esc(m)}</span>' for m in bank)
                 + '</div>')
    return Question(
        type_id="measure_word", title_zh="量词",
        title_en="Measure words",
        instruction_zh="从词库里选出合适的量词，填入括号内。每个词只能用一次。",
        instruction_en="Choose the correct measure word from the bank and write it "
                       "in the brackets. Each word may only be used once.",
        body_html=bank_html + f'<div class="items c3" style="margin-top:2mm">{items}</div>',
        answer_html="　".join(f'{m}（{noun}）' for m, noun in pairs),
        student_hanzi="".join(noun for _, noun in pairs) + "".join(bank),
        solution=[(noun, m) for m, noun in pairs], answer_mode="bijection",
        meta={"bank": bank},
        marks=len(pairs), marks_each=1, items_n=len(pairs),
        est_minutes=0.35 * len(pairs),
    )
