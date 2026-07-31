"""
Rendering layer. Produces one self-contained, print-ready HTML file.

Print contract (do not casually change — consistency is the point):
  * A4 portrait, 12mm/14mm margins
  * every question block is break-inside: avoid
  * answer key always starts on a fresh page
  * no colour is required for correctness; everything reads in greyscale
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

CN_NUM = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八",
          "十九", "二十", "二十一", "二十二", "二十三", "二十四", "二十五"]

# Circled digits for individual questions — headings already use CN_NUM's
# 一/二/三 for section grouping (e.g. "一、字"), so a question numbered the
# same way reads as a second, colliding "section one" right under it.
CIRCLED = ["", "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
           "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]
from datetime import date
from typing import List, Optional

from . import enrich


# --------------------------------------------------------------------------
# Question object — the single contract between qbank and renderer
# --------------------------------------------------------------------------

@dataclass
class Question:
    type_id: str
    title_zh: str
    title_en: str
    instruction_zh: str = ""
    instruction_en: str = ""
    body_html: str = ""
    answer_html: str = ""
    student_hanzi: str = ""      # every Hanzi a student must READ -> leak check
    marks: int = 0
    est_minutes: float = 2.0
    notes: str = ""              # teacher note, printed in the answer key only
    leak_mode: str = "strict"    # "strict" -> blocks; "advisory" -> reported only

    # ---- machine-readable key, checked by zhw.validate before printing ----
    solution: List[tuple] = field(default_factory=list)   # [(prompt, answer), ...]
    answer_mode: str = "unique"  # unique | open | teacher(-> rejected)
    distractors: List[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    # ---- layout ----
    items_n: int = 0             # for the "1 x 24 = 24" tally
    marks_each: int = 1


# --------------------------------------------------------------------------
# Reusable print primitives
# --------------------------------------------------------------------------

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def tianzige(ch: str = "", faded: bool = False, grid: str = "tian",
             size: str = "", pinyin: str = "") -> str:
    """One 田字格 / 米字格 cell. `faded` renders a light model to trace."""
    cls = ["tzg", f"tzg-{grid}"]
    if size:
        cls.append(f"tzg-{size}")
    inner = ""
    if ch:
        inner = f'<span class="{"tzg-model" if faded else "tzg-char"}">{esc(ch)}</span>'
    py = f'<span class="tzg-py">{esc(pinyin)}</span>' if pinyin else ""
    return f'<span class="tzg-wrap">{py}<span class="{" ".join(cls)}">{inner}</span></span>'


def tzg_row(ch: str, boxes: int = 5, models: int = 1, faded: int = 2,
            grid: str = "tian", pinyin: str = "") -> str:
    """A tracing row: solid model(s), faded models to trace, then empty boxes."""
    cells = [tianzige(ch, faded=False, grid=grid, pinyin=pinyin if i == 0 else "")
             for i in range(models)]
    cells += [tianzige(ch, faded=True, grid=grid) for _ in range(faded)]
    cells += [tianzige("", grid=grid) for _ in range(max(0, boxes - models - faded))]
    return f'<div class="tzg-row">{"".join(cells)}</div>'


def stroke_order_svg(ch: str, upto: Optional[int] = None, size: int = 46,
                     highlight_last: bool = True) -> str:
    """Render `ch` showing only the first `upto` strokes (default: all)."""
    paths = enrich.strokes(ch)
    if not paths:
        return f'<span class="so-missing">{esc(ch)}</span>'
    n = len(paths) if upto is None else max(0, min(upto, len(paths)))
    body = []
    for i, p in enumerate(paths[:n]):
        last = highlight_last and i == n - 1
        fill = "#111" if not last else "#111"
        op = "1" if not last else "1"
        body.append(f'<path d="{p}" fill="{fill}" opacity="{op}"/>')
    return (
        f'<svg class="so" width="{size}" height="{size}" viewBox="0 0 1024 1024" '
        f'aria-label="{esc(ch)}">'
        f'<g transform="scale(1,-1) translate(0,-900)">{"".join(body)}</g></svg>'
    )


def stroke_sequence(ch: str, size: int = 40) -> str:
    """The full 笔顺 strip: cumulative stroke build-up, one cell per stroke."""
    paths = enrich.strokes(ch)
    if not paths:
        return ""
    cells = [f'<span class="so-cell">{stroke_order_svg(ch, i + 1, size)}</span>'
             for i in range(len(paths))]
    return f'<span class="so-strip">{"".join(cells)}</span>'


def blank(width: str = "3em", label: str = "") -> str:
    """A ruled blank. Never put this inside brackets — pick one affordance."""
    return f'<span class="blank" style="min-width:{width}">{esc(label)}</span>'


def slot_marker() -> str:
    """Marks WHERE a character is missing from a word — not something to write
    in. Deliberately different from bracket() and blank() so it can never be
    mistaken for an answer space; the answer is chosen by circling a letter."""
    return '<span class="slot">▢</span>'


def bracket(chars: float = 2.0) -> str:
    """A bracketed answer space, sized in approximate hanzi-widths.
    No rule inside — the brackets are the cue, and the glyphs never eat
    into the writing room (they sit outside the sized interior)."""
    return (f'<span class="brk"><span class="brk-l">（</span>'
           f'<span class="brk-i" style="width:{chars}em"></span>'
           f'<span class="brk-r">）</span></span>')


def wordbank(items: List[str], title_zh: str = "词语库", title_en: str = "Word bank") -> str:
    chips = "".join(f'<span class="chip">{esc(i)}</span>' for i in items)
    return (f'<div class="bank"><span class="bank-t">{esc(title_zh)}'
            f'<span class="en"> {esc(title_en)}</span></span>{chips}</div>')


def writing_lines(n: int = 2, boxes: int = 0) -> str:
    if boxes:
        return f'<div class="tzg-row">{"".join(tianzige("") for _ in range(boxes))}</div>'
    return "".join('<div class="wline"></div>' for _ in range(n))


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------

CSS = r"""
:root{
  --ink:#111; --rule:#333; --soft:#8a8a8a; --faint:#c9c9c9; --box:#4a4a4a;
  --accent:#1f4e79; --pad:3.2mm;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:"Noto Sans SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",
              "Hiragino Sans GB",-apple-system,"Segoe UI",Arial,sans-serif;
  color:var(--ink); font-size:10.5pt; line-height:1.5; background:#f4f4f5;
}
.sheet{
  width:210mm; min-height:297mm; margin:8mm auto; padding:12mm 14mm;
  background:#fff; box-shadow:0 1px 8px rgba(0,0,0,.15);
}
.zh{font-family:"Kaiti SC","STKaiti","KaiTi","楷体","AR PL UKai CN",
    "Noto Serif SC",serif;}

/* ---------- header ---------- */
.head{border-bottom:1.6pt solid var(--ink);padding-bottom:2.5mm;margin-bottom:4mm}
.head-top{display:flex;justify-content:space-between;align-items:baseline;gap:6mm}
.h-title{font-size:15pt;font-weight:700;letter-spacing:.5px}
.h-sub{font-size:9pt;color:var(--soft)}
.h-meta{display:flex;gap:5mm;font-size:9.5pt;margin-top:2.5mm;flex-wrap:wrap}
.h-meta span{flex:1 1 auto;white-space:nowrap}
.h-meta u{display:inline-block;min-width:26mm;border-bottom:.8pt solid var(--rule);
          text-decoration:none}
.scopebar{font-size:9pt;color:var(--soft);margin-top:1.5mm}

.sec{margin:5mm 0 3mm;padding:1.2mm 0 1.2mm 2.5mm;border-left:4pt solid var(--ink);
     background:#f0f0f0;font-weight:700;font-size:11.5pt;break-after:avoid;
     page-break-after:avoid}
.sec .en{font-weight:400;font-size:8.5pt;color:#666;margin-left:2mm}

/* ---------- question block ---------- */
.q{margin:0 0 5.5mm;break-inside:avoid;page-break-inside:avoid}
.q-h{display:flex;align-items:baseline;gap:2mm;border-left:2.4pt solid var(--ink);
     padding-left:2.5mm;margin-bottom:2mm}
.q-n{font-weight:700;font-size:11pt}
.q-t{font-weight:700;font-size:11pt}
.q-t .en{font-weight:400;font-size:8.5pt;color:var(--soft);margin-left:1.5mm}
.q-m{margin-left:auto;font-size:8.5pt;color:var(--soft);white-space:nowrap}
.q-i{font-size:9.5pt;color:#333;margin:0 0 2mm 2.5mm}
.q-i .en{color:var(--soft);font-size:8.5pt}
.q-b{margin-left:2.5mm}

/* ---------- 田字格 ---------- */
.tzg-row{display:flex;flex-wrap:wrap;gap:1.5mm;margin:1.5mm 0;align-items:flex-end}
.tzg-wrap{display:inline-flex;flex-direction:column;align-items:center}
.tzg-py{font-size:8pt;color:var(--soft);height:4mm;line-height:4mm}
.tzg{position:relative;width:14mm;height:14mm;border:.9pt solid var(--box);
     display:inline-flex;align-items:center;justify-content:center;flex:none}
.tzg-sm{width:11mm;height:11mm}
.tzg-lg{width:18mm;height:18mm}
.tzg::before,.tzg::after{content:"";position:absolute;border-color:var(--faint);
     border-style:dashed}
.tzg::before{left:0;right:0;top:50%;border-top-width:.7pt;border-top-style:dashed}
.tzg::after{top:0;bottom:0;left:50%;border-left-width:.7pt;border-left-style:dashed}
/* 米字格 adds the two diagonals on top of the 田字格 crosshair; 田字格 needs
   no extra rule beyond .tzg's crosshair, so .tzg-tian is intentionally empty
   rather than a ghost class with nothing behind it */
.tzg-tian{}
.tzg-mi{background:
  linear-gradient(to bottom right, transparent calc(50% - .35pt), var(--faint) calc(50% - .35pt),
    var(--faint) calc(50% + .35pt), transparent calc(50% + .35pt)),
  linear-gradient(to bottom left, transparent calc(50% - .35pt), var(--faint) calc(50% - .35pt),
    var(--faint) calc(50% + .35pt), transparent calc(50% + .35pt))}
.tzg-char,.tzg-model{font-family:"Kaiti SC","STKaiti","KaiTi","楷体",
     "AR PL UKai CN","Noto Serif SC",serif;font-size:11mm;line-height:1}
.tzg-sm .tzg-char,.tzg-sm .tzg-model{font-size:8.5mm}
.tzg-model{color:var(--faint)}

/* ---------- stroke order ---------- */
.so{vertical-align:middle}
.so-strip{display:inline-flex;flex-wrap:wrap;gap:1mm}
.so-cell{border:.7pt solid var(--faint);padding:.4mm;line-height:0;display:inline-block}
.so-missing{font-size:14pt}

/* ---------- generic bits ---------- */
.blank{display:inline-block;border-bottom:.9pt solid var(--rule);
       min-width:3.6em;text-align:center;margin:0 .35em;height:1.7em;vertical-align:bottom}
.wline{border-bottom:.8pt solid var(--faint);height:8mm;margin-top:1mm}
.bank{border:.9pt dashed var(--box);padding:2mm 2.5mm;margin:1.5mm 0;
      display:flex;flex-wrap:wrap;gap:2mm;align-items:center}
.bank-t{font-size:9pt;font-weight:700;color:#444}
.bank-t .en{font-weight:400;color:var(--soft);font-size:8pt}
.chip{font-size:11pt;padding:.3mm 2mm;border:.7pt solid var(--faint);border-radius:1mm}
.items{display:grid;gap:2mm 5mm}
.items.c1{grid-template-columns:1fr}
.items.c2{grid-template-columns:1fr 1fr}
.items.c3{grid-template-columns:1fr 1fr 1fr}
.items.c4{grid-template-columns:repeat(4,1fr)}
.item{display:flex;gap:1.5mm;align-items:baseline;font-size:10.5pt}
.item .lbl{color:var(--soft);font-size:9pt;min-width:5mm}
.big{font-size:15pt}
.opts{display:flex;gap:4mm;flex-wrap:wrap;margin-left:5mm;font-size:10.5pt}
.opt{white-space:nowrap}
.match{display:flex;gap:14mm;justify-content:flex-start}
.match ul{list-style:none;margin:0;padding:0}
.match li{padding:1.2mm 0;font-size:11pt}
.grid-tbl{border-collapse:collapse}
.grid-tbl td{border:.8pt solid var(--box);width:9mm;height:9mm;text-align:center;
   font-family:"Kaiti SC","KaiTi","楷体",serif;font-size:12pt;padding:0}
.pytab{border-collapse:collapse;font-size:10pt}
.pytab td,.pytab th{border:.8pt solid var(--faint);padding:1.2mm 2mm;text-align:center}
.hint{font-size:8.5pt;color:var(--soft)}
.sent{font-size:12pt;line-height:2.1}

/* ---------- answer key ---------- */
.key{break-before:page;page-break-before:always}
.key .sheet-h{font-size:14pt;font-weight:700;border-bottom:1.6pt solid var(--ink);
   padding-bottom:2mm;margin-bottom:4mm}
.a{margin-bottom:3mm;font-size:10pt;break-inside:avoid}
.a-h{font-weight:700}
.a-b{margin-left:4mm}
.a-n{color:var(--accent);font-size:9pt;margin-left:4mm;font-style:italic}

/* ---------- footer ---------- */
.foot{margin-top:6mm;padding-top:2mm;border-top:.8pt solid var(--faint);
      font-size:8pt;color:var(--soft);display:flex;justify-content:space-between}

/* ---------- drill style: dense, plain, classroom ---------- */
body.drill{font-size:11pt}
body.drill .q{margin-bottom:4mm}
body.drill .q-h{border-left:0;padding-left:0;margin-bottom:1mm;gap:1.5mm}
body.drill .q-n{font-weight:700;font-size:11.5pt;min-width:7mm}
body.drill .q-t{font-weight:700;font-size:11.5pt}
body.drill .q-i{margin-left:8mm;color:#000;font-size:9.5pt;margin-bottom:1.5mm}
body.drill .q-b{margin-left:8mm}
body.drill .q-m{font-weight:700;color:#000;font-size:10pt}
body.drill .bank{border:0;justify-content:center;gap:6mm;padding:1mm 0;
   border-top:.8pt solid #999;border-bottom:.8pt solid #999}
body.drill .chip{border:0;font-size:13pt;padding:0}
body.drill .items{gap:2.2mm 6mm}
body.drill .item{font-size:11.5pt}
body.drill .wline{height:7mm;border-bottom:.9pt solid #333}
body.drill .sec{background:none;border-left:0;padding-left:0;font-size:11.5pt;
   border-bottom:.9pt solid #999;margin:4mm 0 2mm}
body.drill .tzg{width:11mm;height:11mm}
body.drill .tzg-char,body.drill .tzg-model{font-size:8.5mm}

/* brace pairs (照例子比一比) */
.pairs{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm 8mm}
.pair{display:flex;align-items:center;gap:1.5mm}
.pair .brace{font-size:26pt;line-height:.8;color:#333;font-weight:200}
.pair .col{display:flex;flex-direction:column;gap:2.5mm}
.pair .row{white-space:nowrap;font-size:12pt}
.pair .row .zh{font-size:13pt}
/* bracketed answer space — brackets are the only cue, no rule inside.
   Structured as glyph + sized interior + glyph so the brackets never eat
   into the writing room, however narrow the interior is asked to be. */
.brk{display:inline-flex;align-items:flex-end;vertical-align:bottom;
     font-size:1.15em;line-height:1}
.brk-l,.brk-r{color:#000}
.brk-i{display:inline-block;height:1.55em;min-width:1.6em}

/* position marker only — never an answer space, so it looks like neither
   .brk nor .blank: no rule, no bracket glyphs, just a small inert square */
.slot{display:inline-block;color:#999;font-size:.85em;vertical-align:2px;
      margin:0 .1em}

/* 看字写拼音 — character on top, writing line below with real headroom
   for tone marks; the section itself gets top clearance so row 1 is never
   cramped against the instruction line */
.pywrite{display:flex;flex-direction:column;align-items:center;gap:2mm;
         margin-top:2mm}
.pywrite .zh{font-size:15pt}
.pywrite-line{display:block;width:15mm;height:6mm;border-bottom:.9pt solid #333}

/* pinyin-over-blank (根据拼音写出中文字词) — two equal slots per cell so the
   pinyin sits precisely above whichever slot is the gap, never guessed */
.pyfill{display:grid;grid-template-columns:repeat(4,1fr);gap:7mm 5mm;margin:2mm 0}
.pyfill .cell{display:flex;text-align:center}
.pyfill .pyfill-slot{display:flex;flex-direction:column;align-items:center;width:11mm}
.pyfill .py{font-size:10pt;color:#000;height:4mm;line-height:4mm}
.pyfill .frag{font-size:14pt;line-height:1.4;font-family:"Kaiti SC","STKaiti",
             "KaiTi","楷体","AR PL UKai CN","Noto Serif SC",serif}
.pyfill .gap{display:inline-block;width:11mm;border-bottom:.9pt solid #333;
             height:1.4em}

/* underlined target words (用划线的词造句) */
.uline{text-decoration:underline;text-underline-offset:2.5px}
.uline-w{text-decoration:underline;text-decoration-style:wavy;text-underline-offset:2.5px}

/* ---------- density ---------- */
body.compact{font-size:9.5pt;line-height:1.35}
body.compact .q{margin-bottom:2.6mm}
body.compact .q-i{margin-bottom:1mm;font-size:8.5pt}
body.compact .tzg{width:9.5mm;height:9.5mm}
body.compact .tzg-char,body.compact .tzg-model{font-size:7.2mm}
body.compact .tzg-row{gap:1mm;margin:1mm 0}
body.compact .wline{height:6.5mm}
body.compact .items{gap:1.2mm 4mm}
body.compact .so-cell{padding:.2mm}
body.compact .bank{padding:1.2mm 2mm;margin:1mm 0}
body.spacious .q{margin-bottom:8mm}
body.spacious .wline{height:11mm}

/* ---------- toolbar (screen only) ---------- */
.bar{position:sticky;top:0;z-index:9;background:#111;color:#fff;padding:2mm 4mm;
     display:flex;gap:4mm;align-items:center;font-size:9pt}
.bar button{font:inherit;background:#fff;color:#111;border:0;border-radius:2px;
     padding:1.2mm 3mm;cursor:pointer}
.bar .sp{margin-left:auto;opacity:.7}
body.nokey .key{display:none}
body.nopy .tzg-py,body.nopy .pyline{visibility:hidden}

@media print{
  body{background:#fff;font-size:10.5pt;
       -webkit-print-color-adjust:exact;print-color-adjust:exact}
  .bar{display:none}
  .sheet{width:auto;min-height:0;margin:0;padding:0;box-shadow:none}
  @page{size:A4 portrait;margin:12mm 14mm}
}
"""

TOOLBAR = """
<div class="bar">
  <button onclick="window.print()">Print / PDF</button>
  <button onclick="document.body.classList.toggle('nokey')">Answer key</button>
  <button onclick="document.body.classList.toggle('nopy')">Pinyin</button>
  <button onclick="cycleDensity()">Density</button>
  <span class="sp">Print at 100% scale · A4 · turn OFF browser headers &amp; footers</span>
</div>
<script>
const D=['','compact','spacious'];let di=0;
function cycleDensity(){document.body.classList.remove('compact','spacious');
 di=(di+1)%3; if(D[di])document.body.classList.add(D[di]);}
</script>
"""


# --------------------------------------------------------------------------
# Worksheet assembly
# --------------------------------------------------------------------------

def render_worksheet(*, title: str, subtitle: str, scope_label: str,
                     questions: List[Question], seed: int, recipe_id: str,
                     density: str = "", show_key: bool = True,
                     school_line: str = "本校 · 内部使用 Internal use",
                     footer_note: str = "", style: str = "workbook",
                     lang: str = "both", show_marks: bool = False,
                     teacher_note: str = "") -> str:
    cn = style == "drill"
    show_en = lang in ("both", "en")
    show_zh = lang in ("both", "zh")

    def bi(zh: str, en: str, en_cls: str = "en") -> str:
        parts = []
        if show_zh and zh:
            parts.append(esc(zh))
        if show_en and en:
            parts.append(f'<span class="{en_cls}">{esc(en)}</span>')
        return " ".join(parts)

    body, keys = [], []
    total_marks = sum(q.marks for q in questions)
    total_min = sum(q.est_minutes for q in questions)

    n = 0
    for q in questions:
        if q.type_id == "heading":
            body.append(f'<div class="sec zh">{bi(q.title_zh, q.title_en.strip())}</div>')
            keys.append(f'<div class="sec zh" style="font-size:10.5pt">'
                        f'{esc(q.title_zh)}</div>')
            continue
        n += 1
        label = f"{CIRCLED[n]}" if cn and n < len(CIRCLED) else f"{n}."
        # No marks on a classroom exercise sheet. Students read a score column
        # as "this is a test". --marks turns it on for an actual assessment.
        tally = ""
        if show_marks and q.marks:
            tally = (f'{q.marks_each} × {q.items_n} = {q.marks}'
                     if q.items_n and q.marks_each * q.items_n == q.marks
                     else f'{q.marks} 分')
        instr = ""
        if (show_zh and q.instruction_zh) or (show_en and q.instruction_en):
            instr = f'<div class="q-i zh">{bi(q.instruction_zh, q.instruction_en)}</div>'
        body.append(
            f'<section class="q">'
            f'<div class="q-h"><span class="q-n">{label}</span>'
            f'<span class="q-t zh">{bi(q.title_zh, q.title_en.strip())}</span>'
            f'<span class="q-m">{tally}</span></div>'
            f'{instr}<div class="q-b">{q.body_html}</div></section>'
        )
        note = f'<div class="a-n">Teacher note: {esc(q.notes)}</div>' if q.notes else ""
        mode = ('<span class="a-n" style="margin:0">（开放题 open）</span>'
                if q.answer_mode == "open" else "")
        keys.append(
            f'<div class="a"><div class="a-h">{label} '
            f'<span class="zh">{esc(q.title_zh)}</span> {mode}</div>'
            f'<div class="a-b">{q.answer_html}</div>{note}</div>'
        )

    score_field = ('<span>得分 Score <u></u></span>' if show_marks else "")
    n_q = sum(1 for q in questions if q.type_id != "heading")
    teacher_line = (f'{n_q} 题 · {sum(q.items_n for q in questions)} 项 · '
                    f'约 {int(round(total_min))} 分钟'
                    + (f' · {total_marks} 分' if show_marks else ""))

    key_block = ""
    if show_key:
        key_block = (
            f'<div class="sheet key"><div class="sheet-h zh">参考答案 '
            f'<span style="font-weight:400;font-size:9pt">Answer key — '
            f'{esc(title)}</span></div>'
            f'<div class="scopebar" style="margin:-2mm 0 4mm">{esc(teacher_line)}'
            f'{" · " + esc(teacher_note) if teacher_note else ""}</div>'
            f'{"".join(keys)}'
            f'<div class="foot"><span>{esc(recipe_id)} · seed {seed}</span>'
            f'<span>Answer key</span></div></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-Hans"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body class="{density} {style}">{TOOLBAR}
<div class="sheet">
  <header class="head">
    <div class="head-top">
      <div><div class="h-title zh">{esc(title)}</div>
           <div class="h-sub">{esc(subtitle)}</div></div>
      <div class="h-sub">{esc(school_line)}</div>
    </div>
    <div class="h-meta">
      <span>姓名 Name <u></u></span><span>班级 Class <u></u></span>
      <span>日期 Date <u></u></span>{score_field}
    </div>
    <div class="scopebar">{esc(scope_label)}</div>
  </header>
  {"".join(body)}
  <div class="foot">
    <span>{esc(recipe_id)} · seed {seed} · {date.today().isoformat()}</span>
    <span>{esc(footer_note)}</span>
  </div>
</div>
{key_block}
</body></html>"""
