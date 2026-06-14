#!/usr/bin/env python3
"""Generate A4 Chinese-character handwriting-practice cards (PDF).

Two layouts are available:

* ``big``  (default) -- two large characters per A4 portrait page, each rotated
  90 deg ("lying down"). A dashed line down the middle marks where to cut; turn
  each half upright and the 米字格 box fills almost the whole card, with the
  pinyin (四线三格 guide) on top.
* ``grid`` -- many small 米字格 cells per page (``--cols`` per row), two cards
  per page, also separated by a cut line. Good for compact practice sheets.

Every cell shows the character inside a 米字格 (solid border, dashed cross and
diagonals) with its pinyin on top in a four-line guide.

Pinyin is resolved per character as:
    1. an inline override in the input, e.g.  重(zhòng)  or  重(zhong4)
    2. the curated reading in chinese_tools/data/pinyin_data.py (single char)
    3. xpinyin's most common reading

Run from the repository root as a module:

    # inline characters -> ./worksheet.pdf
    python -m chinese_tools.cards.worksheet_maker 花 园 门 前

    # a list file -> ./yr1_character_cards.pdf  (name derived from the file)
    python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt

    # override a 多音字 reading
    python -m chinese_tools.cards.worksheet_maker --chars "重(zhòng) 行(háng)"

    # regenerate every *_chars.txt in a folder, writing PDFs beside them
    python -m chinese_tools.cards.worksheet_maker --batch worksheets

    # compact grid sheet instead of big cards
    python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt --layout grid

Requires: Pillow, xpinyin  (pip install Pillow xpinyin)
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from chinese_tools.data.pinyin_data import (
    CHARACTER_PINYIN_ENGLISH_MAPPING,
    decode_pinyin,
)
from chinese_tools.paths import GB2312_FONT
from xpinyin import Pinyin

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
# Character font ships with the repo so output is identical everywhere. Swap in
# a 楷体/Kaiti font via --char-font for more authentic handwriting strokes.
DEFAULT_CHAR_FONT = GB2312_FONT

# Pinyin needs tone-marked vowels (ā á ǎ à ...); pick the first font that has
# them across common platforms. Override with --pinyin-font.
PINYIN_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",            # Linux
    "/Library/Fonts/Arial Unicode.ttf",                          # macOS
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",      # macOS
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",    # macOS
    "C:/Windows/Fonts/arial.ttf",                                # Windows
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def find_pinyin_font():
    for path in PINYIN_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "No pinyin font found. Pass --pinyin-font /path/to/a/font.ttf "
        "(needs tone-marked vowels, e.g. DejaVuSans or Arial Unicode)."
    )


# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Style:
    bg: str = "white"
    grid: tuple = (170, 170, 170)        # 米字格 cross + diagonals
    border: tuple = (90, 90, 90)         # 米字格 outer border
    pinyin_lines: tuple = (180, 180, 180)  # 四线三格 guide
    pinyin_text: tuple = (40, 40, 40)
    char: tuple = (15, 15, 15)
    cut: tuple = (140, 140, 140)


STYLE = Style()


@dataclass
class Config:
    layout: str = "big"          # "big" or "grid"
    dpi: int = 300
    margin_mm: float = 7.0        # outer page margin
    cols: int = 8                # grid layout: cells per row
    pinyin_ratio: float = 0.20   # pinyin band height relative to the box
    title: str = ""
    png: bool = False
    char_font: str = DEFAULT_CHAR_FONT
    pinyin_font: str = ""        # resolved lazily


# A4 portrait, in millimetres.
A4_MM = (210.0, 297.0)
CARDS_PER_PAGE = 2


def mm(value, dpi):
    """Millimetres -> pixels at the given DPI."""
    return round(value / 25.4 * dpi)


# ---------------------------------------------------------------------------
# Input parsing & pinyin resolution
# ---------------------------------------------------------------------------
_ENGINE = Pinyin()


def is_han(ch):
    return "一" <= ch <= "鿿"


def parse_entries(raw):
    """Parse text into a list of (character, pinyin_override_or_None).

    A character may be followed by an explicit reading in parentheses, e.g.
    ``重(zhòng)`` or ``重(zhong4)``. Half-width and full-width parens both work.
    All non-Han characters are ignored.
    """
    entries = []
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if not is_han(ch):
            i += 1
            continue
        j = i + 1
        override = None
        k = j
        while k < n and raw[k] in " \t":
            k += 1
        if k < n and raw[k] in "(（":
            end = k + 1
            while end < n and raw[end] not in ")）":
                end += 1
            override = raw[k + 1:end].strip() or None
            j = end + 1
        entries.append((ch, override))
        i = j
    return entries


def normalize_pinyin(text):
    """Accept tone marks as-is; convert numbered pinyin (zhong4) to marks."""
    if any(c.isdigit() for c in text):
        return "".join(decode_pinyin(tok) for tok in text.split())
    return text


def resolve_pinyin(char, override):
    if override:
        return normalize_pinyin(override)
    entry = CHARACTER_PINYIN_ENGLISH_MAPPING.get(char)
    if entry and entry[0]:
        return entry[0]
    return _ENGINE.get_pinyin(char, "", tone_marks="marks")


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------
def dashed_line(draw, p0, p1, color, width, dash, gap):
    x0, y0 = p0
    x1, y1 = p1
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist == 0:
        return
    ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
    pos = 0.0
    while pos < dist:
        end = min(pos + dash, dist)
        draw.line([(x0 + ux * pos, y0 + uy * pos),
                   (x0 + ux * end, y0 + uy * end)], fill=color, width=width)
        pos += dash + gap


def draw_pinyin_grid(draw, x0, x1, y_top, height, pinyin, font,
                     width, dash, gap):
    """四线三格 four-line guide; pinyin seated on the third line."""
    pad = int(height * 0.12)
    top = y_top + pad
    band = (height - 2 * pad) / 3.0
    lines = [top + band * i for i in range(4)]
    draw.line([(x0, lines[0]), (x1, lines[0])], fill=STYLE.pinyin_lines, width=width)
    draw.line([(x0, lines[3]), (x1, lines[3])], fill=STYLE.pinyin_lines, width=width)
    dashed_line(draw, (x0, lines[1]), (x1, lines[1]), STYLE.pinyin_lines, width, dash, gap)
    dashed_line(draw, (x0, lines[2]), (x1, lines[2]), STYLE.pinyin_lines, width, dash, gap)
    if pinyin:
        draw.text(((x0 + x1) / 2, lines[2]), pinyin,
                  fill=STYLE.pinyin_text, font=font, anchor="ms")


def draw_mizige(draw, bx, by, box, char, font, width, border, dash, gap):
    """米字格 box: solid border, dashed cross + diagonals, centered char."""
    right, bottom = bx + box, by + box
    cx, cy = bx + box // 2, by + box // 2
    dashed_line(draw, (bx, cy), (right, cy), STYLE.grid, width, dash, gap)
    dashed_line(draw, (cx, by), (cx, bottom), STYLE.grid, width, dash, gap)
    dashed_line(draw, (bx, by), (right, bottom), STYLE.grid, width, dash, gap)
    dashed_line(draw, (right, by), (bx, bottom), STYLE.grid, width, dash, gap)
    draw.rectangle([bx, by, right, bottom], outline=STYLE.border, width=border)
    if char:
        draw.text((cx, cy), char, fill=STYLE.char, font=font, anchor="mm")


# ---------------------------------------------------------------------------
# Layout: big (two rotated characters per page)
# ---------------------------------------------------------------------------
def _make_card(char, pinyin, box, pinyin_h, char_font, pinyin_font,
               line_w, border_w, dash, gap, side_pad):
    """One upright card (pinyin guide on top, 米字格 below) before rotation."""
    top_pad = bot_pad = side_pad
    mid_gap = max(6, side_pad // 2)
    w = box + 2 * side_pad
    h = top_pad + pinyin_h + mid_gap + box + bot_pad
    card = Image.new("RGB", (w, h), STYLE.bg)
    draw = ImageDraw.Draw(card)
    draw_pinyin_grid(draw, side_pad, side_pad + box, top_pad, pinyin_h,
                     pinyin, pinyin_font, line_w, dash, gap)
    draw_mizige(draw, side_pad, top_pad + pinyin_h + mid_gap, box, char,
                char_font, line_w, border_w, dash, gap)
    return card


def render_big(entries, cfg, char_font_path, pinyin_font_path):
    dpi = cfg.dpi
    page_w, page_h = mm(A4_MM[0], dpi), mm(A4_MM[1], dpi)
    margin = mm(cfg.margin_mm, dpi)
    side_pad = mm(2.5, dpi)
    card_h = (page_h - 2 * margin) // 2
    usable_w = page_w - 2 * margin

    box = card_h - 2 * side_pad - mm(0.5, dpi)
    pinyin_h = int(box * cfg.pinyin_ratio)
    line_w = max(2, mm(0.18, dpi))
    border_w = max(3, mm(0.4, dpi))
    dash, gap = max(mm(2, dpi), box // 38), max(mm(1.2, dpi), box // 60)

    char_font = ImageFont.truetype(char_font_path, int(box * 0.82))
    pinyin_font = ImageFont.truetype(pinyin_font_path, int(pinyin_h * 0.5))
    label_font = ImageFont.truetype(pinyin_font_path, mm(4, dpi))

    readings = [resolve_pinyin(c, o) for c, o in entries]
    chars = [c for c, _ in entries]
    pages = []
    for p in range(max(1, (len(chars) + 1) // 2)):
        img = Image.new("RGB", (page_w, page_h), STYLE.bg)
        draw = ImageDraw.Draw(img)
        for slot in range(CARDS_PER_PAGE):
            gi = p * CARDS_PER_PAGE + slot
            if gi >= len(chars):
                continue
            card = _make_card(chars[gi], readings[gi], box, pinyin_h,
                              char_font, pinyin_font, line_w, border_w,
                              dash, gap, side_pad)
            card = card.rotate(90, expand=True, fillcolor=STYLE.bg)
            cw, ch = card.size
            region_top = margin + slot * card_h
            img.paste(card, (margin + (usable_w - cw) // 2,
                             region_top + (card_h - ch) // 2))
        _draw_cut_line(draw, page_w, margin, margin + card_h, dpi, label_font)
        pages.append(img)
    return pages


# ---------------------------------------------------------------------------
# Layout: grid (many small cells per page)
# ---------------------------------------------------------------------------
def render_grid(entries, cfg, char_font_path, pinyin_font_path):
    dpi = cfg.dpi
    page_w, page_h = mm(A4_MM[0], dpi), mm(A4_MM[1], dpi)
    margin = mm(cfg.margin_mm, dpi)
    inner = mm(6, dpi)
    cols = max(1, cfg.cols)
    card_h = (page_h - 2 * margin) // 2

    cell_w = (page_w - 2 * margin - 2 * inner) // cols
    cell_h = int(cell_w / (1 - cfg.pinyin_ratio))
    rows = max(1, (card_h - 2 * inner) // cell_h)
    per_card = cols * rows
    per_page = per_card * CARDS_PER_PAGE

    box = int(cell_w * 0.88)
    pinyin_h = int(cell_h * cfg.pinyin_ratio)
    line_w = max(2, mm(0.15, dpi))
    border_w = max(2, mm(0.3, dpi))
    dash, gap = max(mm(1.5, dpi), box // 28), max(mm(1, dpi), box // 44)
    char_font = ImageFont.truetype(char_font_path, int(box * 0.78))
    pinyin_font = ImageFont.truetype(pinyin_font_path, int(pinyin_h * 0.46))
    label_font = ImageFont.truetype(pinyin_font_path, mm(4, dpi))

    readings = [resolve_pinyin(c, o) for c, o in entries]
    chars = [c for c, _ in entries]
    pages = []
    for p in range(max(1, (len(chars) + per_page - 1) // per_page)):
        img = Image.new("RGB", (page_w, page_h), STYLE.bg)
        draw = ImageDraw.Draw(img)
        for slot in range(CARDS_PER_PAGE):
            gx = margin + inner
            gy = margin + slot * card_h + inner
            base = p * per_page + slot * per_card
            for idx in range(per_card):
                gi = base + idx
                if gi >= len(chars):
                    break
                r, c = divmod(idx, cols)
                cx, cy = gx + c * cell_w, gy + r * cell_h
                pad = (cell_w - box) // 2
                draw_pinyin_grid(draw, cx + pad, cx + pad + box, cy, pinyin_h,
                                 readings[gi], pinyin_font, line_w, dash, gap)
                draw_mizige(draw, cx + pad, cy + pinyin_h, box, chars[gi],
                            char_font, line_w, border_w, dash, gap)
        _draw_cut_line(draw, page_w, margin, margin + card_h, dpi, label_font)
        pages.append(img)
    return pages


def _draw_cut_line(draw, page_w, margin, y, dpi, font):
    dashed_line(draw, (margin // 2, y), (page_w - margin // 2, y),
                STYLE.cut, width=2, dash=mm(1.8, dpi), gap=mm(1.3, dpi))
    draw.text((page_w - margin // 2, y - mm(2.5, dpi)), "✂ cut",
              fill=STYLE.cut, font=font, anchor="rm")


RENDERERS = {"big": render_big, "grid": render_grid}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def save_pdf(pages, out_prefix, dpi, also_png=False):
    """Save a grayscale multi-page PDF (and optionally per-page PNGs)."""
    os.makedirs(os.path.dirname(out_prefix) or ".", exist_ok=True)
    gray = [page.convert("L") for page in pages]  # lossless here, much smaller
    pdf_path = out_prefix + ".pdf"
    gray[0].save(pdf_path, "PDF", resolution=dpi,
                 save_all=True, append_images=gray[1:])
    if also_png:
        for i, page in enumerate(gray, 1):
            page.save(f"{out_prefix}_p{i:02d}.png", "PNG",
                      dpi=(dpi, dpi), optimize=True)
    return pdf_path


def build(entries, out_prefix, cfg):
    pinyin_font = cfg.pinyin_font or find_pinyin_font()
    renderer = RENDERERS[cfg.layout]
    pages = renderer(entries, cfg, cfg.char_font, pinyin_font)
    pdf_path = save_pdf(pages, out_prefix, cfg.dpi, cfg.png)
    return pdf_path, len(pages)


def derive_name(input_path):
    """yr1_chars.txt -> yr1_character_cards (drop a trailing '_chars')."""
    base = os.path.splitext(os.path.basename(input_path))[0]
    if base.endswith("_chars"):
        base = base[:-len("_chars")]
    return base + "_character_cards"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_argument_group("input (choose one)")
    src.add_argument("chars", nargs="*", help="characters inline")
    src.add_argument("--chars", dest="chars_str", default="",
                     help="characters as one string (supports 字(pinyin))")
    src.add_argument("--file", help="read characters from a text file")
    src.add_argument("--batch", metavar="DIR",
                     help="process every *_chars.txt (or *.txt) in DIR")

    out = p.add_argument_group("output")
    out.add_argument("--out", help="output path prefix (single input)")
    out.add_argument("--outdir", help="output directory (default: input's dir)")
    out.add_argument("--png", action="store_true",
                     help="also write per-page PNGs")

    fmt = p.add_argument_group("format")
    fmt.add_argument("--layout", choices=list(RENDERERS), default="big",
                     help="'big' (2 big cards/A4, default) or 'grid'")
    fmt.add_argument("--cols", type=int, default=8,
                     help="grid layout: cells per row (default 8)")
    fmt.add_argument("--dpi", type=int, default=300, help="render DPI")
    fmt.add_argument("--margin-mm", type=float, default=7.0,
                     help="outer page margin in mm")
    fmt.add_argument("--char-font", default=DEFAULT_CHAR_FONT,
                     help="character TTF (try a Kaiti/楷体 for practice strokes)")
    fmt.add_argument("--pinyin-font", default="",
                     help="pinyin TTF (default: auto-detect)")
    return p


def config_from_args(args):
    return Config(layout=args.layout, dpi=args.dpi, margin_mm=args.margin_mm,
                  cols=args.cols, png=args.png, char_font=args.char_font,
                  pinyin_font=args.pinyin_font)


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = config_from_args(args)

    if args.batch:
        files = sorted(glob.glob(os.path.join(args.batch, "*_chars.txt"))) \
            or sorted(glob.glob(os.path.join(args.batch, "*.txt")))
        if not files:
            print(f"No .txt lists found in {args.batch}", file=sys.stderr)
            return 1
        outdir = args.outdir or args.batch
        for path in files:
            with open(path, encoding="utf-8") as fh:
                entries = parse_entries(fh.read())
            if not entries:
                print(f"skip (no characters): {path}")
                continue
            prefix = os.path.join(outdir, derive_name(path))
            pdf, n = build(entries, prefix, cfg)
            print(f"{os.path.basename(path):20s} -> {pdf}  ({len(entries)} chars, {n} pages)")
        return 0

    raw = " ".join(args.chars) + " " + args.chars_str
    src_path = None
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            raw += " " + fh.read()
        src_path = args.file

    entries = parse_entries(raw)
    if not entries:
        print("No characters provided. See --help for usage.", file=sys.stderr)
        return 1

    if args.out:
        prefix = args.out
    elif src_path:
        outdir = args.outdir or os.path.dirname(src_path) or "."
        prefix = os.path.join(outdir, derive_name(src_path))
    else:
        prefix = os.path.join(args.outdir or ".", "worksheet")

    pdf, n = build(entries, prefix, cfg)
    print(f"{len(entries)} characters, {n} pages -> {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
