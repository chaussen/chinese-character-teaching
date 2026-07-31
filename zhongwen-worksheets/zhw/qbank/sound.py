"""拼音 — pinyin and sound question types."""

from __future__ import annotations

from typing import Optional

from .. import enrich
from ..render import Question, tianzige, blank, esc, wordbank
from ..render import slot_marker
from . import register, Ctx


def _key(py: str) -> str:
    return py.replace(" ", "").lower()


@register("pinyin_write", "看字写拼音", "Write the pinyin", "sound",
          needs=("chars",), default_count=8, minutes_each=0.4)
def pinyin_write(ctx: Ctx) -> Optional[Question]:
    # 多音字 and auto-filled readings both make "the" pinyin arguable
    chars = ctx.pick([c for c in ctx.chars()
                      if ctx.unambiguous_pinyin(c.char)], ctx.count)
    if not chars:
        return None
    items = "".join(
        f'<div class="pywrite">'
        f'<span class="zh">{esc(c.char)}</span>'
        f'<span class="pywrite-line"></span></div>'
        for c in chars)
    ans = "　".join(f'{c.char} {c.pinyin}' for c in chars)
    return Question(
        type_id="pinyin_write", title_zh="看字写拼音", title_en="Write the pinyin",
        instruction_zh="看汉字，在下面的横线上写出拼音，注意声调。",
        instruction_en="Look at each character and write its pinyin on the line below. Mark the tone.",
        body_html=f'<div class="items c4" style="gap:5mm 6mm">{items}</div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=[(c.char, c.pinyin) for c in chars], answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.4 * len(chars),
    )


@register("pinyin_read", "看拼音写汉字", "Write the character", "sound",
          needs=("chars",), default_count=8, minutes_each=0.5)
def pinyin_read(ctx: Ctx) -> Optional[Question]:
    # single characters are too often homophonous — words only, and the word's
    # reading must not be shared by another in-scope word
    words = [w for w in ctx.words() if len(w.word) >= 2 and w.pinyin]
    by_reading = {}
    for w in ctx.all_words():
        by_reading.setdefault(_key(w.pinyin), set()).add(w.word)
    src = ctx.pick([w for w in words if len(by_reading.get(_key(w.pinyin), ())) == 1],
                   ctx.count)
    if not src:
        return None
    items, keys, hz = [], [], []
    for i, s in enumerate(src, 1):
        text = getattr(s, "word", None) or s.char
        py = s.pinyin or enrich.auto_pinyin(text)
        boxes = "".join(tianzige("", size="sm") for _ in text)
        items.append(f'<div class="item" style="flex-direction:column;'
                     f'align-items:flex-start;gap:.5mm">'
                     f'<span style="font-size:9.5pt;color:#555">({i}) {esc(py)}</span>'
                     f'<span>{boxes}</span></div>')
        keys.append(f'({i}) {text}')
        hz.append(text)
    return Question(
        type_id="pinyin_read", title_zh="看拼音写汉字", title_en="Write the characters",
        instruction_zh="读拼音，把汉字写在田字格里。",
        instruction_en="Read the pinyin and write the characters in the boxes.",
        body_html=f'<div class="items c3" style="gap:3mm 6mm">{"".join(items)}</div>',
        answer_html="　".join(keys), student_hanzi="",  # student reads pinyin only
        solution=[(k, k.split(") ")[-1]) for k in keys], answer_mode="unique",
        marks=len(items), marks_each=1, items_n=len(items),
        est_minutes=0.5 * len(items),
    )


@register("tone_mark", "标出声调", "Mark the tone", "sound",
          needs=("chars",), default_count=8, minutes_each=0.3)
def tone_mark(ctx: Ctx) -> Optional[Question]:
    chars = [c for c in ctx.pick(ctx.chars(), ctx.count) if c.pinyin]
    if not chars:
        return None
    items = "".join(
        f'<div class="item"><span class="lbl">({i})</span>'
        f'<span class="zh big">{esc(c.char)}</span>'
        f'<span style="font-size:11pt;letter-spacing:1px">'
        f'{esc(enrich.strip_tone(c.pinyin))}</span>'
        f'<span style="color:#888">→</span>{blank("4.5em")}</div>'
        for i, c in enumerate(chars, 1))
    ans = "　".join(f'({i}) {c.pinyin}（{enrich.tone_of(c.pinyin)}声）'
                   for i, c in enumerate(chars, 1))
    return Question(
        type_id="tone_mark", title_zh="标出声调", title_en="Add the tone mark",
        instruction_zh="拼音少了声调，请补上，重新写一遍。",
        instruction_en="The tone marks are missing. Rewrite each pinyin with its tone.",
        body_html=f'<div class="items c2">{items}</div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=[(enrich.strip_tone(c.pinyin), c.pinyin) for c in chars],
        answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.3 * len(chars),
    )


@register("pinyin_match", "连一连", "Match pinyin to character", "sound",
          needs=("chars",), default_count=6, minutes_each=0.4)
def pinyin_match(ctx: Ctx) -> Optional[Question]:
    # pre-filter: two characters sharing a reading make the link ambiguous
    cand, seen = [], set()
    for c in ctx.shuffled([c for c in ctx.chars()
                           if ctx.unambiguous_pinyin(c.char)]):
        if c.pinyin in seen:
            continue
        seen.add(c.pinyin)
        cand.append(c)
    chars = cand[:ctx.count]
    if len(chars) < 3:
        return None
    right = ctx.shuffled(chars)
    left = "".join(f'<li><span class="zh">{esc(c.char)}</span>　●</li>' for c in chars)
    rights = "".join(f'<li>●　{esc(c.pinyin)}</li>' for c in right)
    ans = "　".join(f'{c.char}–{c.pinyin}' for c in chars)
    return Question(
        type_id="pinyin_match", title_zh="连一连", title_en="Match with a line",
        instruction_zh="把汉字和它的拼音用线连起来。",
        instruction_en="Draw a line from each character to its pinyin.",
        body_html=f'<div class="match"><ul>{left}</ul><ul>{rights}</ul></div>',
        answer_html=ans, student_hanzi="".join(c.char for c in chars),
        solution=[(c.char, c.pinyin) for c in chars], answer_mode="bijection",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.4 * len(chars),
    )


@register("homophone", "选字组词（同音字）", "Choose the character that completes the word (homophones)", "sound",
          needs=("chars",), default_count=4, minutes_each=0.5)
def homophone(ctx: Ctx) -> Optional[Question]:
    pool = [c.char for c in ctx.all_chars()]
    vocab = {w.word for w in ctx.all_words()}
    rows, keys, hz, sol, dw = [], [], [], [], []
    for c in ctx.shuffled(ctx.chars()):
        hs = enrich.homophones(c.char, pool, ctx.pinyin_of)
        if not hs:
            continue
        opts = ctx.shuffled([c.char, hs[0]])
        words = [w.word for w in ctx.words() if c.char in w.word]
        if not words:
            continue
        target = words[0]
        wrong = target.replace(c.char, hs[0], 1)
        if wrong in vocab:            # the distractor also makes a real word
            continue
        dw.append(wrong)
        rest = target.replace(c.char, "", 1)
        rows.append(
            f'<div class="item" style="display:block;margin-bottom:1.5mm">'
            f'<span class="lbl">({len(rows)+1})</span> '
            f'{slot_marker()}<span class="zh big">{esc(rest)}</span>　'
            f'{"　".join(f"{chr(65+j)}. <span class=zh>{esc(o)}</span>" for j, o in enumerate(opts))}'
            f'</div>')
        keys.append(f'({len(rows)}) {chr(65+opts.index(c.char))} {target}')
        sol.append((rest, c.char))
        hz.append(target + "".join(opts))
        if len(rows) >= ctx.count:
            break
    if not rows:
        return None
    return Question(
        type_id="homophone", title_zh="选字组词（同音字）",
        title_en="Choose the character that completes the word (homophones)",
        instruction_zh="□处缺一个字，读音相同的选项里只有一个能跟旁边的字组成学过的词语，圈出那个字母。",
        instruction_en="The □ shows a missing character. The options all sound the same, "
                       "but only one completes a word you have learned — circle that letter.",
        body_html="".join(rows), answer_html="　".join(keys),
        student_hanzi="".join(hz), solution=sol, answer_mode="unique",
        meta={"distractor_words": dw},
        marks=len(rows), marks_each=1, items_n=len(rows),
        est_minutes=0.5 * len(rows),
    )
