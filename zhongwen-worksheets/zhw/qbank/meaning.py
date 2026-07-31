"""词义 — meaning and vocabulary question types."""

from __future__ import annotations

from typing import Optional

from ..render import Question, blank, esc, wordbank, tianzige
from . import register, Ctx


@register("gloss_match", "中英连线", "Match to English", "meaning",
          needs=("chars",), default_count=6, minutes_each=0.4)
def gloss_match(ctx: Ctx) -> Optional[Question]:
    # pre-filter: identical or nested glosses make the link ambiguous
    # an auto-filled gloss is dictionary English, not the meaning taught in class
    src_pool = [x for x in (ctx.words() or ctx.chars())
                if getattr(x, "gloss", "")
                and "gloss" not in getattr(x, "derived", set())]
    cand, seen = [], []
    for x in ctx.shuffled(src_pool):
        g = x.gloss.strip().lower()
        if any(g == h or g in h or h in g for h in seen):
            continue
        seen.append(g)
        cand.append(x)
    src = cand[:ctx.count]
    if len(src) < 3:
        return None
    right = ctx.shuffled(src)
    left = "".join(
        f'<li><span class="zh">{esc(getattr(x, "word", None) or x.char)}</span>　●</li>'
        for x in src)
    rights = "".join(f'<li>●　{esc(x.gloss)}</li>' for x in right)
    ans = "　".join(f'{getattr(x, "word", None) or x.char}–{x.gloss}' for x in src)
    return Question(
        type_id="gloss_match", title_zh="中英连线", title_en="Match Chinese to English",
        instruction_zh="把中文和英文的意思连起来。",
        instruction_en="Draw a line from each Chinese item to its English meaning.",
        body_html=f'<div class="match"><ul>{left}</ul><ul>{rights}</ul></div>',
        answer_html=ans,
        student_hanzi="".join(getattr(x, "word", None) or x.char for x in src),
        solution=[(getattr(x, "word", None) or x.char, x.gloss) for x in src],
        answer_mode="bijection",
        marks=len(src), marks_each=1, items_n=len(src), est_minutes=0.4 * len(src),
    )


@register("make_words", "组词", "Make words", "meaning",
          needs=("chars",), default_count=6, minutes_each=0.6,
          confidence="open")
def make_words(ctx: Ctx) -> Optional[Question]:
    """Only offers a blank position (character-first or character-last) when
    the taught vocabulary contains a real example there. A character that only
    appears mid-word, or not at all in the word list, is skipped rather than
    padded with an unsupported slot."""
    words = ctx.all_words()

    def prefix_words(ch):
        return [w.word for w in words if len(w.word) >= 2 and w.word[0] == ch]

    def suffix_words(ch):
        # a doubled character (AA reduplication, e.g. 悄悄) starts AND ends
        # with ch — it already counts as a prefix example, so counting it
        # again here would render two slots (ch__ / __ch) with the same
        # single word as the answer to both, which just looks like a bug.
        return [w.word for w in words if len(w.word) >= 2 and w.word[-1] == ch
                and w.word != ch * 2]

    candidates = []
    for c in ctx.write_chars():
        pre, suf = prefix_words(c.char), suffix_words(c.char)
        if pre or suf:
            candidates.append((c, pre, suf))
    if not candidates:
        return None
    chosen = ctx.pick(candidates, ctx.count)

    rows, keys, slot_count = [], [], 0
    for i, (c, pre, suf) in enumerate(chosen, 1):
        slots = []
        if pre:
            slots.append(f'{esc(c.char)}{blank("3.2em")}')
            slot_count += 1
        if suf:
            slots.append(f'{blank("3.2em")}{esc(c.char)}')
            slot_count += 1
        rows.append(f'<div class="item"><span class="lbl">({i})</span>'
                    f'<span class="zh" style="font-size:12pt">{"　".join(slots)}</span></div>')
        parts = []
        if pre:
            parts.append(f'{c.char}＿：' + "、".join(pre[:3]))
        if suf:
            parts.append(f'＿{c.char}：' + "、".join(suf[:3]))
        keys.append(f'({i}) ' + "；".join(parts))
    return Question(
        type_id="make_words", title_zh="组词", title_en="Make words",
        instruction_zh="用这个字组成课本里学过的词语。",
        instruction_en="Use each character to make words you have learned.",
        body_html=f'<div class="items c2">{"".join(rows)}</div>',
        answer_html="　".join(keys),
        student_hanzi="".join(c.char for c, _, _ in chosen),
        answer_mode="open",
        marks=slot_count, marks_each=1, items_n=len(chosen),
        est_minutes=0.6 * len(chosen),
        notes="Accept any correct word, not only the ones listed — these are the in-scope examples. "
              "Only positions (character-first / character-last) with a real taught example are shown.",
    )


@register("antonym", "写出反义词", "Antonyms", "meaning",
          needs=("antonyms",), default_count=6, minutes_each=0.3)
def antonym(ctx: Ctx) -> Optional[Question]:
    pairs = ctx.scope.target_antonyms() or [
        p for ls in ctx.scope.allowed_lessons for p in ls.antonyms]
    pairs = ctx.pick(pairs, ctx.count)
    if not pairs:
        return None
    bank = wordbank(ctx.shuffled([p[1] for p in pairs]), "词语库", "Word bank")
    items = "".join(
        f'<div class="item"><span class="lbl">({i})</span>'
        f'<span class="zh big">{esc(p[0])}</span>　↔　{blank("3.5em")}</div>'
        for i, p in enumerate(pairs, 1))
    ans = "　".join(f'({i}) {p[0]}↔{p[1]}' for i, p in enumerate(pairs, 1))
    return Question(
        type_id="antonym", title_zh="写出反义词", title_en="Write the opposite",
        instruction_zh="从词语库里选出意思相反的词。",
        instruction_en="Choose the word with the opposite meaning from the bank.",
        body_html=bank + f'<div class="items c3">{items}</div>',
        answer_html=ans,
        student_hanzi="".join("".join(p) for p in pairs),
        solution=[(p[0], p[1]) for p in pairs], answer_mode="bijection",
        marks=len(pairs), marks_each=1, items_n=len(pairs),
        est_minutes=0.3 * len(pairs),
    )


@register("word_meaning_mcq", "圈出正确的词语", "Word meaning choice", "meaning",
          needs=("words",), default_count=5, minutes_each=0.4)
def word_meaning_mcq(ctx: Ctx) -> Optional[Question]:
    words = [w for w in ctx.all_words()
             if w.gloss and "gloss" not in getattr(w, "derived", set())]
    if len(words) < 4:
        return None
    rows, keys, hz = [], [], []
    wsel = ctx.pick(words, ctx.count)
    for i, w in enumerate(wsel, 1):
        wrong = [x.word for x in ctx.pick([x for x in words if x.word != w.word], 3)]
        opts = ctx.shuffled([w.word] + wrong)
        rows.append(f'<div class="item" style="display:block;margin-bottom:1.5mm">'
                    f'<span class="lbl">({i})</span> <b>{esc(w.gloss)}</b>　'
                    f'{"　".join(f"{chr(65+j)}. <span class=zh>{esc(o)}</span>" for j, o in enumerate(opts))}'
                    f'</div>')
        keys.append(f'({i}) {chr(65+opts.index(w.word))} {w.word}')
        hz.append("".join(opts))
    return Question(
        type_id="word_meaning_mcq", title_zh="圈出正确的词语",
        title_en="Circle the matching word",
        instruction_zh="读英文意思，圈出正确的中文词语。",
        instruction_en="Read the English meaning and circle the correct Chinese word.",
        body_html="".join(rows), answer_html="　".join(keys),
        student_hanzi="".join(hz),
        solution=[(w.gloss, w.word) for w in wsel], answer_mode="unique",
        marks=len(rows), marks_each=1, items_n=len(rows),
        est_minutes=0.4 * len(rows),
    )


@register("word_build_boxes", "抄写词语", "Copy the words", "production",
          needs=("words",), default_count=6, minutes_each=0.8,
          confidence="open")
def word_build_boxes(ctx: Ctx) -> Optional[Question]:
    words = ctx.pick(ctx.words(), ctx.count)
    if not words:
        return None
    rows = []
    for w in words:
        model = "".join(tianzige(ch, faded=False, size="sm") for ch in w.word)
        faded = "".join(tianzige(ch, faded=True, size="sm") for ch in w.word)
        empty = "".join(tianzige("", size="sm") for ch in w.word) * 2
        rows.append(f'<div class="item" style="align-items:center;gap:3mm;margin-bottom:1mm">'
                    f'<span style="font-size:8.5pt;color:#777;min-width:16mm">{esc(w.pinyin)}</span>'
                    f'{model}{faded}{empty}</div>')
    return Question(
        type_id="word_build_boxes", title_zh="抄写词语", title_en="Copy the words",
        instruction_zh="照着写，先描后写。",
        instruction_en="Copy each word: trace first, then write it yourself.",
        body_html="".join(rows),
        answer_html="书写练习。 Handwriting task — check character order and spacing.",
        student_hanzi="".join(w.word for w in words), answer_mode="open",
        marks=len(words), marks_each=1, items_n=len(words),
        est_minutes=0.8 * len(words),
    )
