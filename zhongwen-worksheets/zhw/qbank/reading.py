"""阅读 — reading question types.

Passages are NEVER machine-written. They come from the lesson's `passage`
field (課文 / 阅读) or are assembled from the lesson's own sentences.
"""

from __future__ import annotations

import re
from typing import Optional

from ..render import Question, bracket, esc, writing_lines
from . import register, Ctx

PUNCT = "，。？！、；："


@register("passage_read", "读一读，回答问题", "Read and answer", "reading",
          needs=("passage", "comprehension"), default_count=5, minutes_each=1.2,
          confidence="authored",
          blurb="Passage plus teacher-authored questions. The auto version was "
                "removed: distorting a sentence does not reliably make it false.")
def passage_read(ctx: Ctx) -> Optional[Question]:
    passages = ctx.scope.target_passages()
    if not passages:
        return None
    text = passages[0]
    tf = [(t, bool(ok)) for t, ok in ctx.scope.target_authored("truefalse")
          if len(str(t)) >= 2]
    qa = [(q, a) for q, a in ctx.scope.target_authored("comprehension")]
    if not tf and not qa:
        return None

    body = (f'<div class="zh" style="font-size:12pt;line-height:2.1;'
            f'border:.9pt solid #4a4a4a;padding:3mm;margin-bottom:2.5mm">'
            f'{esc(text)}</div>')
    sol, keys, n = [], [], 0
    if tf:
        tf = ctx.pick(tf, max(1, ctx.count // 2))
        body += ('<div style="font-size:9.5pt;color:#333;margin:1.5mm 0 1mm">'
                 '对的画 ✓，错的画 ✗。 Tick or cross.</div>')
        for t, ok in tf:
            n += 1
            body += (f'<div class="item sent"><span class="lbl">({n})</span>'
                     f'<span class="zh">{esc(t)}</span>　{bracket(1.2)}</div>')
            sol.append((t, "✓" if ok else "✗"))
            keys.append(f'({n}) {"✓" if ok else "✗"}')
    if qa:
        qa = ctx.pick(qa, max(1, ctx.count - len(tf)))
        body += ('<div style="font-size:9.5pt;color:#333;margin:2mm 0 1mm">'
                 '回答问题。 Answer the questions.</div>')
        for q, a in qa:
            n += 1
            body += (f'<div style="margin-bottom:1mm"><div class="item sent">'
                     f'<span class="lbl">({n})</span>'
                     f'<span class="zh">{esc(q)}</span></div>{writing_lines(1)}</div>')
            sol.append((q, a))
            keys.append(f'({n}) {a}')
    return Question(
        type_id="passage_read", title_zh="读一读，回答问题",
        title_en="Read the passage and answer",
        instruction_zh="先读短文，再做下面的题。",
        instruction_en="Read the passage, then answer the questions below.",
        body_html=body,
        answer_html="　".join(esc(k) for k in keys)
                    + "<br><span class='hint'>问答题接受意思相同的说法。 "
                      "Accept any answer with the same meaning.</span>",
        student_hanzi=text + "".join(str(x) for x, _ in sol),
        solution=sol, answer_mode="unique",
        marks=n, marks_each=1, items_n=n, est_minutes=1.2 * n,
    )


@register("sentence_order", "排一排", "Put the sentences in order", "reading",
          needs=("passage",), default_count=4, minutes_each=1.0,
          confidence="authored",
          risk="Runs only on a real 课文 paragraph, where the printed order is the "
               "answer. Some paragraphs still permit a defensible alternative.")
def sentence_order(ctx: Ctx) -> Optional[Question]:
    passages = ctx.scope.target_passages()
    text = passages[0] if passages else ""
    sents = [s.strip() for s in re.split(r"(?<=[。！？])", text) if s.strip()]
    if len(sents) < 3:
        return None          # an unordered example list has no single right order
    ordered = sents[:min(ctx.count, len(sents))]
    shown = ctx.shuffled(ordered)
    rows = "".join(
        f'<div class="item sent">{bracket(1.3)}'
        f'<span class="zh">{esc(s)}</span></div>' for s in shown)
    key = "　".join(f'{shown.index(s)+1}→{i+1}' for i, s in enumerate(ordered))
    return Question(
        type_id="sentence_order", title_zh="排一排", title_en="Put them in order",
        instruction_zh="在括号里写上序号，把句子排成一段通顺的话。",
        instruction_en="Number the sentences so they form a sensible paragraph.",
        body_html=rows,
        answer_html="正确顺序 Correct order: " + " / ".join(esc(s) for s in ordered)
                    + f'<br><span class="hint">{key}</span>',
        student_hanzi="".join(ordered),
        solution=[(s, str(i + 1)) for i, s in enumerate(ordered)],
        answer_mode="bijection", meta={"from_passage": True},
        marks=len(ordered), marks_each=1, items_n=len(ordered),
        est_minutes=1.0 * len(ordered),
    )


@register("free_write", "写一写", "Free writing", "production",
          needs=(), default_count=1, minutes_each=8.0,
          confidence="open")
def free_write(ctx: Ctx) -> Optional[Question]:
    prompt_zh = ctx.p("prompt_zh", "用本课学过的词语写几句话。")
    prompt_en = ctx.p("prompt_en", "Write a few sentences using this lesson's words.")
    lines = ctx.p("lines", 6)
    words = [w.word for w in ctx.words()][:8]
    from ..render import wordbank
    bank = wordbank(words, "可以用", "You may use") if words else ""
    box = ctx.p("picture_box", True)
    pic = ('<div style="border:.9pt dashed #4a4a4a;height:34mm;margin:2mm 0;'
           'display:flex;align-items:center;justify-content:center;color:#aaa;'
           'font-size:9pt">画一画 Draw here</div>') if box else ""
    return Question(
        type_id="free_write", title_zh="写一写", title_en="Write",
        instruction_zh=prompt_zh, instruction_en=prompt_en,
        body_html=pic + bank + writing_lines(lines),
        answer_html="自由作答。 Open response. Mark on: in-scope vocabulary use, "
                    "sentence completeness, punctuation, character accuracy.",
        student_hanzi="".join(words), answer_mode="open",
        marks=6, marks_each=6, items_n=1, est_minutes=8.0,
    )
