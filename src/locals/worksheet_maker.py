#!/usr/bin/env python3
"""Generate A4 character-practice worksheets.

Layout: every A4 page holds TWO cards (top half + bottom half) separated by a
dashed cut line, so a printed page can be cut in half. Each card is filled with
米字格 (mizige) cells, and every cell shows the character's pinyin on top.

Characters flow continuously: top card, then bottom card, then the next page.

Usage:
    python worksheet_maker.py 花 园 门 前              # characters as arguments
    python worksheet_maker.py --chars "花园门前个他"     # one string
    python worksheet_maker.py --file chars.txt          # read from a file
    python worksheet_maker.py --chars "花园" --cols 8 --out practice/worksheet

Output: a multi-page PDF (<out>.pdf) plus per-page PNG previews (<out>_p1.png ...).
"""
import argparse
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

# Pinyin: prefer the curated single-character readings already in the repo,
# fall back to xpinyin for anything not listed.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
try:
    from character_pinyin_constants import CHARACTER_PINYIN_ENGLISH_MAPPING
except Exception:
    CHARACTER_PINYIN_ENGLISH_MAPPING = {}
from xpinyin import Pinyin

# ---------------------------------------------------------------------------
# Page / layout configuration (A4 at 300 DPI, portrait)
# ---------------------------------------------------------------------------
DPI = 300
A4_W, A4_H = 2480, 3508          # A4 portrait in pixels @ 300 DPI
PAGE_MARGIN = 110                # outer page margin
CARDS_PER_PAGE = 2               # two cards stacked => cut in half
CARD_INNER_MARGIN = 70           # margin inside each card
DEFAULT_COLS = 8                 # cells per row

# Cell proportions
PINYIN_RATIO = 0.30              # pinyin header height as a fraction of the box
CELL_PAD = 0.06                  # padding around the character box within a cell

# Colours
BG_COLOR = "white"
GRID_COLOR = (170, 170, 170)     # 米字格 lines (light gray, ink-friendly)
BORDER_COLOR = (90, 90, 90)      # outer box border
CHAR_COLOR = (15, 15, 15)
PINYIN_COLOR = (40, 40, 40)
CUT_COLOR = (140, 140, 140)

PINYIN_LINE_COLOR = (180, 180, 180)  # 四线三格 guide lines

GRID_WIDTH = 2
BORDER_WIDTH = 3
DASH_LEN = 18
DASH_GAP = 12

# Fonts
_HERE = os.path.dirname(__file__)
CHAR_FONT_PATH = os.path.join(_HERE, "GB2312.ttf")
PINYIN_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

_pinyin_engine = Pinyin()


def get_pinyin(char):
    """Return the pinyin (with tone marks) for a single character."""
    entry = CHARACTER_PINYIN_ENGLISH_MAPPING.get(char)
    if entry and entry[0]:
        return entry[0]
    return _pinyin_engine.get_pinyin(char, "", tone_marks="marks")


def extract_characters(raw):
    """Pull every CJK character out of the raw input, preserving order."""
    return re.findall(r"[一-鿿]", raw)


def dashed_line(draw, p0, p1, color, width=2, dash=DASH_LEN, gap=DASH_GAP):
    """Draw a dashed line between two arbitrary points."""
    x0, y0 = p0
    x1, y1 = p1
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist == 0:
        return
    ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
    n = 0.0
    while n < dist:
        e = min(n + dash, dist)
        draw.line([(x0 + ux * n, y0 + uy * n),
                   (x0 + ux * e, y0 + uy * e)], fill=color, width=width)
        n += dash + gap


def draw_pinyin_grid(draw, x0, x1, y_top, height, pinyin, pinyin_font):
    """Draw a 四线三格 (four-line) guide and seat the pinyin on the 3rd line."""
    pad = int(height * 0.12)
    top = y_top + pad
    band = (height - 2 * pad) / 3.0
    lines = [top + band * i for i in range(4)]
    # outer lines solid, inner two dashed (classic look)
    draw.line([(x0, lines[0]), (x1, lines[0])],
              fill=PINYIN_LINE_COLOR, width=GRID_WIDTH)
    draw.line([(x0, lines[3]), (x1, lines[3])],
              fill=PINYIN_LINE_COLOR, width=GRID_WIDTH)
    dashed_line(draw, (x0, lines[1]), (x1, lines[1]), PINYIN_LINE_COLOR)
    dashed_line(draw, (x0, lines[2]), (x1, lines[2]), PINYIN_LINE_COLOR)
    if pinyin:
        # baseline on the 3rd line -> body sits in the middle band,
        # tone marks / ascenders rise into the top band.
        draw.text(((x0 + x1) / 2, lines[2]), pinyin,
                  fill=PINYIN_COLOR, font=pinyin_font, anchor="ms")


def draw_cell(draw, x, y, cell_w, cell_h, char, pinyin, char_font, pinyin_font):
    """Draw one cell: a 四线三格 pinyin guide on top, then a 米字格 box."""
    pinyin_h = int(cell_h * PINYIN_RATIO)
    pad = int(cell_w * CELL_PAD)
    box = min(cell_w, cell_h - pinyin_h) - 2 * pad
    bx = x + (cell_w - box) // 2
    by = y + pinyin_h + (cell_h - pinyin_h - box) // 2

    # --- pinyin on top, inside a four-line guide aligned to the box ---
    right, bottom = bx + box, by + box
    draw_pinyin_grid(draw, bx, right, y, pinyin_h, pinyin, pinyin_font)

    # --- 米字格 box: solid border, dashed cross + diagonals ---
    mx, my = bx + box // 2, by + box // 2
    dashed_line(draw, (bx, my), (right, my), GRID_COLOR)
    dashed_line(draw, (mx, by), (mx, bottom), GRID_COLOR)
    dashed_line(draw, (bx, by), (right, bottom), GRID_COLOR)
    dashed_line(draw, (right, by), (bx, bottom), GRID_COLOR)
    draw.rectangle([bx, by, right, bottom], outline=BORDER_COLOR,
                   width=BORDER_WIDTH)

    # --- character, centered in the box ---
    if char:
        draw.text((mx, my), char, fill=CHAR_COLOR, font=char_font, anchor="mm")


def layout():
    """Compute cell grid geometry shared by every page."""
    cols = layout.cols
    card_h = (A4_H - 2 * PAGE_MARGIN) // CARDS_PER_PAGE
    inner_w = A4_W - 2 * PAGE_MARGIN - 2 * CARD_INNER_MARGIN
    inner_h = card_h - 2 * CARD_INNER_MARGIN
    cell_w = inner_w // cols
    # cell height: square box + pinyin header
    cell_h = int(cell_w / (1 - PINYIN_RATIO))
    rows = max(1, inner_h // cell_h)
    return cols, rows, cell_w, cell_h, card_h


layout.cols = DEFAULT_COLS


def render(characters, out_prefix, title=""):
    cols, rows, cell_w, cell_h, card_h = layout()
    per_card = cols * rows
    per_page = per_card * CARDS_PER_PAGE

    char_size = int(cell_w * 0.74)
    pinyin_size = int(cell_h * PINYIN_RATIO * 0.46)
    char_font = ImageFont.truetype(CHAR_FONT_PATH, char_size)
    pinyin_font = ImageFont.truetype(PINYIN_FONT_PATH, pinyin_size)
    title_font = ImageFont.truetype(PINYIN_FONT_PATH, 46)

    pinyins = [get_pinyin(c) for c in characters]
    total_pages = max(1, (len(characters) + per_page - 1) // per_page)
    pages = []

    for p in range(total_pages):
        img = Image.new("RGB", (A4_W, A4_H), BG_COLOR)
        draw = ImageDraw.Draw(img)

        for card in range(CARDS_PER_PAGE):
            card_top = PAGE_MARGIN + card * card_h
            grid_x = PAGE_MARGIN + CARD_INNER_MARGIN
            grid_y = card_top + CARD_INNER_MARGIN

            if title:
                draw.text((grid_x, card_top + 12), title, fill=(110, 110, 110),
                          font=title_font, anchor="lm")

            base = p * per_page + card * per_card
            for idx in range(per_card):
                gi = base + idx
                if gi >= len(characters):
                    break
                r, c = divmod(idx, cols)
                cx = grid_x + c * cell_w
                cy = grid_y + r * cell_h
                draw_cell(draw, cx, cy, cell_w, cell_h,
                          characters[gi], pinyins[gi], char_font, pinyin_font)

        # cut line between the two cards
        cut_y = PAGE_MARGIN + card_h
        dashed_line(draw, (PAGE_MARGIN // 2, cut_y),
                    (A4_W - PAGE_MARGIN // 2, cut_y), CUT_COLOR,
                    width=2, dash=22, gap=16)
        draw.text((A4_W - PAGE_MARGIN // 2, cut_y - 30), "✂ cut",
                  fill=CUT_COLOR, font=pinyin_font, anchor="rm")

        pages.append(img)

    os.makedirs(os.path.dirname(out_prefix) or ".", exist_ok=True)
    pdf_path = out_prefix + ".pdf"
    pages[0].save(pdf_path, "PDF", resolution=DPI,
                  save_all=True, append_images=pages[1:])
    png_paths = []
    for i, page in enumerate(pages, 1):
        pp = f"{out_prefix}_p{i}.png"
        page.save(pp, "PNG", dpi=(DPI, DPI))
        png_paths.append(pp)

    return pdf_path, png_paths, len(characters), per_page, total_pages


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chars", nargs="*", help="characters as arguments")
    parser.add_argument("--chars", dest="chars_str", default="",
                        help="characters as a single string")
    parser.add_argument("--file", help="read characters from a text file")
    parser.add_argument("--out", default="practice/worksheet",
                        help="output path prefix (default: practice/worksheet)")
    parser.add_argument("--title", default="", help="optional header text")
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS,
                        help=f"cells per row (default: {DEFAULT_COLS})")
    args = parser.parse_args(argv)

    raw = " ".join(args.chars) + " " + args.chars_str
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            raw += " " + fh.read()

    characters = extract_characters(raw)
    if not characters:
        characters = extract_characters("花园门前个他后外年季儿看")
        print("No characters provided; using a sample set.")

    layout.cols = max(1, args.cols)
    pdf_path, png_paths, n, per_page, pages = render(
        characters, args.out, args.title)
    print(f"Characters: {n}  |  per page: {per_page}  |  pages: {pages}")
    print(f"PDF:  {pdf_path}")
    for pp in png_paths:
        print(f"PNG:  {pp}")


if __name__ == "__main__":
    main()
