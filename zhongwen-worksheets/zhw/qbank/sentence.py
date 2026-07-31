"""句子 — sentence and grammar question types.

All sentence material is taken from the ingested lesson data. Nothing here
composes new Chinese sentences; it only re-presents textbook sentences as
scrambles, cloze items and models.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..render import Question, blank, esc, wordbank, writing_lines
from . import register, Ctx

PUNCT = "，。？！、；：“”‘’《》…—"

# ，and ；separate independent clauses; 、only lists items WITHIN a clause
# (视觉、听觉) and is deliberately not a split point here.
CLAUSE_BREAK = re.compile("[，；]")


def _segment(sentence: str) -> List[str]:
    """Split a sentence into chunks for scrambling: word list first, else chars."""
    s = re.sub(f"[{PUNCT}]", "", sentence)
    return list(s)


def _segment_by_words(sentence: str, words: List[str]) -> List[str]:
    """Greedy longest-match segmentation using the in-scope word list."""
    s = re.sub(f"[{PUNCT}]", "", sentence)
    vocab = sorted({w for w in words if len(w) >= 2}, key=lambda w: (-len(w), w))
    out, i = [], 0
    while i < len(s):
        for w in vocab:
            if s.startswith(w, i):
                out.append(w)
                i += len(w)
                break
        else:
            out.append(s[i])
            i += 1
    return out


_QUOTES_ETC = "“”‘’《》…—"


def _clauses(sentence: str) -> List[str]:
    """Split a textbook sentence into its natural clauses at internal commas
    and semicolons, so a long compound/complex sentence — normal in a book 9
    课文 — doesn't turn into an unworkable 20+-chunk scramble. Still verbatim
    textbook wording, just presented one clause at a time. 、is left alone:
    it lists items WITHIN a clause (视觉、听觉), not between clauses."""
    s = re.sub(f"[{_QUOTES_ETC}。！？]", "", sentence.strip())
    return [p for p in CLAUSE_BREAK.split(s) if p]


@register("scramble", "连词成句", "Unscramble the sentence", "sentence",
          needs=("sentences",), default_count=4, minutes_each=1.0,
          confidence="open",
          risk="Chunks can often be validly reordered (我和哥哥 / 哥哥和我), so the "
               "textbook sentence is the model answer, not the only answer. A "
               "long compound sentence (common by book 9) is split into its "
               "natural clauses first via `_clauses`, and each candidate is "
               "capped at `max_chunks` pieces, so a puzzle never balloons past "
               "what a student can actually work through.")
def scramble(ctx: Ctx) -> Optional[Question]:
    vocab = [w.word for w in ctx.all_words()]
    hard_cap = ctx.p("max_chunks", 10)
    candidates = []
    for s in ctx.scope.target_sentences():
        for clause in _clauses(s):
            chunks = _segment_by_words(clause, vocab)
            if 3 <= len(chunks) <= hard_cap:
                candidates.append((clause, chunks))
    if not candidates:
        return None
    # bias hard toward the shortest available clauses — "not the single
    # longest option" is still too long for a reorder puzzle a kid should be
    # able to finish, so sort short-first and sample from that end.
    candidates.sort(key=lambda c: len(c[1]))
    pool = candidates[: max(ctx.count * 2, ctx.count + 2)]
    chosen = ctx.pick(pool, min(ctx.count, len(pool)))
    if not chosen:
        return None
    rows, keys, hz = [], [], []
    for i, (clause, chunks) in enumerate(chosen, 1):
        shown = ctx.shuffled(chunks)
        rows.append(
            f'<div style="margin-bottom:2.5mm"><div class="item">'
            f'<span class="lbl">({i})</span>'
            f'<span class="zh" style="font-size:12pt">'
            f'{"　｜　".join(esc(c) for c in shown)}</span></div>'
            f'{writing_lines(1)}</div>')
        keys.append(f'({i}) {clause}')
        hz.append(clause)
    return Question(
        type_id="scramble", title_zh="连词成句", title_en="Make a sentence",
        instruction_zh="把词语排成一句通顺的话，加上标点。",
        instruction_en="Put the words in order to make a sentence. Add punctuation.",
        body_html="".join(rows),
        answer_html="课文原句（节选）Textbook clause:<br>" + "<br>".join(esc(k) for k in keys)
                    + "<br><b>接受任何通顺、标点正确、用上全部词语的句子。</b> "
                      "Accept any fluent, correctly punctuated sentence that uses "
                      "every chunk.",
        student_hanzi="".join(hz), answer_mode="open",
        marks=len(rows) * 2, marks_each=2, items_n=len(rows),
        est_minutes=1.0 * len(rows),
    )


@register("cloze", "选词填空", "Fill in the blanks", "sentence",
          needs=("cloze",), default_count=6, minutes_each=0.6,
          confidence="authored",
          blurb="Only runs on teacher-authored gap items. Auto-generated cloze was "
                "removed: code cannot tell whether a second bank word also fits.")
def cloze(ctx: Ctx) -> Optional[Question]:
    items = [x for x in ctx.scope.target_authored("cloze") if len(x) >= 2]
    items = ctx.pick(items, ctx.count)
    if len(items) < 2:
        return None
    answers = [a for _, a in items]
    if len(set(answers)) != len(answers):
        return None                      # two gaps with the same word is not a key
    bank = wordbank(ctx.shuffled(answers), "词语库", "Word bank")
    rows = "".join(
        f'<div class="item sent"><span class="lbl">({i})</span>'
        f'<span class="zh">{esc(sent)}</span></div>'
        for i, (sent, _) in enumerate(items, 1))
    gaps = [(sent.replace("＿＿", a).replace("___", a), a) for sent, a in items]
    return Question(
        type_id="cloze", title_zh="选词填空", title_en="Choose and fill in",
        instruction_zh="从词语库里选出合适的词，填在横线上。每个词只用一次。",
        instruction_en="Choose the right word for each blank. Each word is used once.",
        body_html=bank + rows,
        answer_html="　".join(f'({i}) {a}' for i, (_, a) in enumerate(items, 1)),
        student_hanzi="".join(sent for sent, _ in items) + "".join(answers),
        solution=[(sent, a) for sent, a in items], answer_mode="bijection",
        meta={"gaps": gaps, "bank": answers},
        marks=len(items), marks_each=1, items_n=len(items),
        est_minutes=0.6 * len(items),
    )


@register("pattern_write", "照样子写句子", "Write like the example", "sentence",
          needs=("patterns",), default_count=3, minutes_each=2.0,
          confidence="open")
def pattern_write(ctx: Ctx) -> Optional[Question]:
    pats = ctx.pick(ctx.scope.target_patterns(), ctx.count)
    sents = ctx.scope.target_sentences()
    if not pats:
        return None
    rows = []
    for i, p in enumerate(pats, 1):
        example = next((s for s in sents if _pattern_match(p, s)), "")
        eg = (f'<div class="hint">例：<span class="zh">{esc(example)}</span></div>'
              if example else "")
        rows.append(f'<div style="margin-bottom:3mm"><div class="item">'
                    f'<span class="lbl">({i})</span>'
                    f'<span class="zh" style="font-size:12pt">{esc(p)}</span></div>'
                    f'{eg}{writing_lines(2)}</div>')
    return Question(
        type_id="pattern_write", title_zh="照样子写句子", title_en="Write your own sentence",
        instruction_zh="用这个句型，自己写一句话。",
        instruction_en="Use the sentence pattern to write your own sentence.",
        body_html="".join(rows),
        answer_html="自由作答。 Open response — mark on correct use of the pattern, "
                    "in-scope vocabulary and punctuation.",
        student_hanzi="".join(pats) + "".join(
            s for s in sents if any(_pattern_match(p, s) for p in pats)),
        answer_mode="open",
        marks=len(pats) * 2, marks_each=2, items_n=len(pats),
        est_minutes=2.0 * len(pats),
    )


def _pattern_match(pattern: str, sentence: str) -> bool:
    parts = [p for p in re.split(r"[…\.\s]+", pattern) if p]
    return all(p in sentence for p in parts) if parts else False
