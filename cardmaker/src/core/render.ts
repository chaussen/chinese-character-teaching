import { PDFDocument, PDFFont, PDFPage, rgb, degrees } from "pdf-lib";
import fontkit from "@pdf-lib/fontkit";
import type { CharacterDict, Config, Entry, Rgb, StrokeData, Style } from "./types.js";
import { DEFAULT_STYLE } from "./types.js";
import { resolvePinyin, resolveEnglish } from "./pinyin.js";

/** Fonts + curated dictionary the renderer needs, supplied by the host. */
export interface Assets {
  charFont: Uint8Array;
  pinyinFont: Uint8Array;
  dict: CharacterDict;
  /** Per-character stroke data loader (CLI: package; web: CDN). */
  loadStrokes?: (char: string) => Promise<StrokeData | null>;
}

// A4 portrait in PostScript points (72 pt / inch).
const A4: [number, number] = [595.2756, 841.8898];
const mm = (v: number): number => (v / 25.4) * 72;

interface LineOpts {
  color: Rgb;
  thickness: number;
  dash?: [number, number];
}

/**
 * Draws into a card-local coordinate space and maps every point through an
 * affine transform [a b c d e f] (pageX = a*x + c*y + e, pageY = b*x + d*y + f).
 * This lets the "big" layout's rotated cards be authored upright and rendered
 * sideways as true vector content.
 */
class Pen {
  readonly angle: number;
  constructor(
    private readonly page: PDFPage,
    private readonly t: [number, number, number, number, number, number],
  ) {
    this.angle = (Math.atan2(t[1], t[0]) * 180) / Math.PI;
  }
  private map(x: number, y: number): [number, number] {
    const [a, b, c, d, e, f] = this.t;
    return [a * x + c * y + e, b * x + d * y + f];
  }
  line(x0: number, y0: number, x1: number, y1: number, o: LineOpts): void {
    const [sx, sy] = this.map(x0, y0);
    const [ex, ey] = this.map(x1, y1);
    this.page.drawLine({
      start: { x: sx, y: sy },
      end: { x: ex, y: ey },
      thickness: o.thickness,
      color: rgb(...o.color),
      dashArray: o.dash,
    });
  }
  rect(x: number, y: number, w: number, h: number, o: LineOpts): void {
    this.line(x, y, x + w, y, o);
    this.line(x + w, y, x + w, y + h, o);
    this.line(x + w, y + h, x, y + h, o);
    this.line(x, y + h, x, y, o);
  }
  /** Draw `text` with its baseline-left at local (x, y), honouring rotation. */
  text(x: number, y: number, text: string, font: PDFFont, size: number, color: Rgb): void {
    const [px, py] = this.map(x, y);
    this.page.drawText(text, { x: px, y: py, size, font, color: rgb(...color), rotate: degrees(this.angle) });
  }
}

/** Baseline-left point that centres `text` in a box centred on (cx, cy). */
function centered(font: PDFFont, size: number, text: string, cx: number, cy: number): [number, number] {
  const w = font.widthOfTextAtSize(text, size);
  const full = font.heightAtSize(size);
  const asc = font.heightAtSize(size, { descender: false });
  const desc = full - asc;
  return [cx - w / 2, cy - full / 2 + desc];
}

function drawMizige(
  pen: Pen,
  bx: number,
  by: number,
  box: number,
  char: string,
  charFont: PDFFont,
  charSize: number,
  color: Rgb,
  style: Style,
  lineW: number,
  borderW: number,
  dash: [number, number],
): void {
  const right = bx + box;
  const top = by + box;
  const cx = bx + box / 2;
  const cy = by + box / 2;
  const grid: LineOpts = { color: style.grid, thickness: lineW, dash };
  pen.line(bx, cy, right, cy, grid); // horizontal
  pen.line(cx, by, cx, top, grid); // vertical
  pen.line(bx, by, right, top, grid); // diagonal /
  pen.line(right, by, bx, top, grid); // diagonal \
  pen.rect(bx, by, box, box, { color: style.border, thickness: borderW });
  if (char) {
    const [tx, ty] = centered(charFont, charSize, char, cx, cy);
    pen.text(tx, ty, char, charFont, charSize, color);
  }
}

function drawPinyinGuide(
  pen: Pen,
  x0: number,
  x1: number,
  yBottom: number,
  height: number,
  pinyin: string,
  pinyinFont: PDFFont,
  pinyinSize: number,
  style: Style,
  lineW: number,
  dash: [number, number],
  padFrac = 0.12,
): void {
  const pad = height * padFrac;
  const top = yBottom + height - pad;
  const band = (height - 2 * pad) / 3;
  const lines = [0, 1, 2, 3].map((i) => top - band * i);
  const solid: LineOpts = { color: style.pinyinLines, thickness: lineW };
  const dashed: LineOpts = { color: style.pinyinLines, thickness: lineW, dash };
  pen.line(x0, lines[0]!, x1, lines[0]!, solid);
  pen.line(x0, lines[3]!, x1, lines[3]!, solid);
  pen.line(x0, lines[1]!, x1, lines[1]!, dashed);
  pen.line(x0, lines[2]!, x1, lines[2]!, dashed);
  if (pinyin) {
    const w = pinyinFont.widthOfTextAtSize(pinyin, pinyinSize);
    pen.text((x0 + x1) / 2 - w / 2, lines[2]!, pinyin, pinyinFont, pinyinSize, style.pinyinText);
  }
}

function drawCutLine(page: PDFPage, pageW: number, margin: number, y: number, style: Style): void {
  page.drawLine({
    start: { x: margin / 2, y },
    end: { x: pageW - margin / 2, y },
    thickness: 1,
    color: rgb(...style.cut),
    dashArray: [mm(1.8), mm(1.3)],
  });
}

// --- Layout: big (two rotated characters per page) -------------------------
function renderBig(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
  _englishes: string[],
  _strokes: Map<string, StrokeData | null>,
  cfg: Config,
  charFont: PDFFont,
  pinyinFont: PDFFont,
  style: Style,
): void {
  const [pageW, pageH] = A4;
  const margin = mm(cfg.marginMm);
  const sidePad = mm(2.5);
  const halfPage = pageH / 2; // physical half-sheet height — we cut here

  const box = halfPage - 2 * margin - 2 * sidePad; // 米字格 nearly fills the half
  const pinyinH = box * 0.5; // pinyin band ~1/3 of the upright card — as prominent as the character
  const padFrac = 0.05; // small inner pad -> taller guide zones so big pinyin fits within the lines
  const padGuide = pinyinH * padFrac; // four-line guide's inner padding
  const wc = box + 2 * sidePad; // card width (becomes vertical after the 90° rotation)
  const hc = 2 * sidePad + box + pinyinH - padGuide; // card height (becomes horizontal)

  const lineW = mm(0.45); // thicker grid/guide lines — readable from across a room
  const borderW = mm(0.8);
  const dash: [number, number] = [Math.max(mm(2), box / 38), Math.max(mm(1.2), box / 60)];
  const charSize = box * 0.82;
  const pinyinSize = pinyinH * 0.52; // sits inside the four lines (body in the middle zone)

  const pages = Math.max(1, Math.ceil(chars.length / 2));
  for (let p = 0; p < pages; p++) {
    const page = doc.addPage(A4);
    for (let slot = 0; slot < 2; slot++) {
      const gi = p * 2 + slot;
      if (gi >= chars.length) continue;
      const slotBottom = slot === 0 ? halfPage : 0; // slot 0 = top half-sheet
      const ex = (pageW - hc) / 2; // centre across the full page width
      const ey = slotBottom + (halfPage - wc) / 2; // centre on the physical half-sheet
      // rotate 90deg CCW then translate so the card bbox sits at (ex, ey)
      const pen = new Pen(page, [0, 1, -1, 0, ex + hc, ey]);
      const boxBottom = sidePad;
      const boxTop = sidePad + box;
      // trace mode on the big card: render the character faint to be traced over.
      const charColor = cfg.trace > 0 ? style.trace : style.char;
      drawMizige(pen, sidePad, boxBottom, box, chars[gi]!, charFont, charSize, charColor, style, lineW, borderW, dash);
      // seat the pinyin guide so its bottom line meets the box top (no gap)
      const pinyinBottom = boxTop - padGuide;
      drawPinyinGuide(pen, sidePad, sidePad + box, pinyinBottom, pinyinH, readings[gi]!, pinyinFont, pinyinSize, style, lineW, dash, padFrac);
    }
    drawCutLine(page, pageW, margin, halfPage, style);
  }
}

// --- Layout: grid (many small cells per page) ------------------------------
function renderGrid(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
  _englishes: string[],
  _strokes: Map<string, StrokeData | null>,
  cfg: Config,
  charFont: PDFFont,
  pinyinFont: PDFFont,
  style: Style,
): void {
  const [pageW, pageH] = A4;
  const margin = mm(cfg.marginMm);
  const inner = mm(6);
  const cols = Math.max(1, cfg.cols);
  const halfH = (pageH - 2 * margin) / 2;

  const cellW = (pageW - 2 * margin - 2 * inner) / cols;
  const cellH = cellW / (1 - cfg.pinyinRatio);
  const rows = Math.max(1, Math.floor((halfH - 2 * inner) / cellH));
  const perCard = cols * rows;
  const perPage = perCard * 2;

  const box = cellW * 0.88;
  const pad = (cellW - box) / 2;
  const pinyinH = cellH * cfg.pinyinRatio;
  const lineW = mm(0.15);
  const borderW = mm(0.3);
  const dash: [number, number] = [Math.max(mm(1.5), box / 28), Math.max(mm(1), box / 44)];
  const charSize = box * 0.78;
  const pinyinSize = pinyinH * 0.46;

  const newPen = (page: PDFPage) => new Pen(page, [1, 0, 0, 1, 0, 0]);
  const cell = (pn: Pen, x0: number, cellTop: number, char: string, reading: string, color: Rgb): void => {
    drawPinyinGuide(pn, x0 + pad, x0 + pad + box, cellTop - pinyinH, pinyinH, reading, pinyinFont, pinyinSize, style, lineW, dash);
    drawMizige(pn, x0 + pad, cellTop - pinyinH - box, box, char, charFont, charSize, color, style, lineW, borderW, dash);
  };
  const cellTopAt = (regionTop: number, r: number): number => regionTop - inner - r * cellH;
  const xAt = (c: number): number => margin + inner + c * cellW;

  // Trace mode: one character per row — [solid][faint x trace][blank...] —
  // so a learner copies the model across the row. trace 0 keeps cells packed.
  const trace = Math.max(0, Math.min(cfg.trace, cols - 1));
  if (trace > 0) {
    const perPageRows = rows * 2;
    const pages = Math.max(1, Math.ceil(chars.length / perPageRows));
    for (let p = 0; p < pages; p++) {
      const page = doc.addPage(A4);
      const pn = newPen(page);
      for (let slot = 0; slot < 2; slot++) {
        const regionTop = margin + (2 - slot) * halfH;
        for (let r = 0; r < rows; r++) {
          const gi = p * perPageRows + slot * rows + r;
          if (gi >= chars.length) break;
          const cellTop = cellTopAt(regionTop, r);
          for (let c = 0; c < cols; c++) {
            if (c === 0) cell(pn, xAt(c), cellTop, chars[gi]!, readings[gi]!, style.char);
            else if (c <= trace) cell(pn, xAt(c), cellTop, chars[gi]!, "", style.trace);
            else cell(pn, xAt(c), cellTop, "", "", style.char); // blank box to write in
          }
        }
      }
      drawCutLine(page, pageW, margin, margin + halfH, style);
    }
    return;
  }

  const pages = Math.max(1, Math.ceil(chars.length / perPage));
  for (let p = 0; p < pages; p++) {
    const page = doc.addPage(A4);
    const pn = newPen(page);
    for (let slot = 0; slot < 2; slot++) {
      const regionTop = margin + (2 - slot) * halfH; // slot 0 = top
      const base = p * perPage + slot * perCard;
      for (let idx = 0; idx < perCard; idx++) {
        const gi = base + idx;
        if (gi >= chars.length) break;
        const r = Math.floor(idx / cols);
        const c = idx % cols;
        cell(pn, xAt(c), cellTopAt(regionTop, r), chars[gi]!, readings[gi]!, style.char);
      }
    }
    drawCutLine(page, pageW, margin, margin + halfH, style);
  }
}

/** Greedy word-wrap to a maximum width, capped at `maxLines` (… on overflow). */
function wrapText(text: string, font: PDFFont, size: number, maxW: number, maxLines: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const trial = line ? `${line} ${w}` : w;
    if (font.widthOfTextAtSize(trial, size) <= maxW || !line) {
      line = trial;
    } else {
      lines.push(line);
      line = w;
      if (lines.length === maxLines) break;
    }
  }
  if (line && lines.length < maxLines) lines.push(line);
  if (lines.length === maxLines && words.length) {
    // crude overflow check: if the last word isn't present, add an ellipsis
    const joined = lines.join(" ");
    if (font.widthOfTextAtSize(joined, size) < font.widthOfTextAtSize(text, size) - 1) {
      lines[maxLines - 1] = lines[maxLines - 1]!.replace(/\s*\S*$/, "") + " …";
    }
  }
  return lines;
}

// --- Layout: vocab (char/word + pinyin + English flashcards) ---------------
function renderVocab(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
  englishes: string[],
  _strokes: Map<string, StrokeData | null>,
  cfg: Config,
  charFont: PDFFont,
  pinyinFont: PDFFont,
  style: Style,
): void {
  const [pageW, pageH] = A4;
  const margin = mm(cfg.marginMm);
  const cols = Math.min(Math.max(1, cfg.cols), 6);
  const gridW = pageW - 2 * margin;
  const cardW = gridW / cols;
  const cardH = cardW * 0.72;
  const rows = Math.max(1, Math.floor((pageH - 2 * margin) / cardH));
  const perPage = rows * cols;

  const borderW = mm(0.25);
  const pinyinSize = Math.min(cardH * 0.16, cardW * 0.3);
  const engSize = cardH * 0.1;
  const maxCharSize = cardH * 0.46;
  const maxCharW = cardW * 0.84;

  const pages = Math.max(1, Math.ceil(chars.length / perPage));
  for (let p = 0; p < pages; p++) {
    const page = doc.addPage(A4);
    const pen = new Pen(page, [1, 0, 0, 1, 0, 0]);
    for (let idx = 0; idx < perPage; idx++) {
      const gi = p * perPage + idx;
      if (gi >= chars.length) break;
      const r = Math.floor(idx / cols);
      const c = idx % cols;
      const x0 = margin + c * cardW;
      const yTop = pageH - margin - r * cardH; // top edge of this card (y-up)
      const cxc = x0 + cardW / 2;

      pen.rect(x0, yTop - cardH, cardW, cardH, { color: style.cut, thickness: borderW });

      // pinyin (top)
      const reading = readings[gi]!;
      if (reading) {
        const w = pinyinFont.widthOfTextAtSize(reading, pinyinSize);
        pen.text(cxc - w / 2, yTop - cardH * 0.16 - pinyinSize * 0.3, reading, pinyinFont, pinyinSize, style.pinyinText);
      }

      // character / word (middle), autosized to fit the card width
      const word = chars[gi]!;
      const probe = charFont.widthOfTextAtSize(word, 100);
      const charSize = Math.min(maxCharSize, (100 * maxCharW) / Math.max(1, probe));
      const [tx, ty] = centered(charFont, charSize, word, cxc, yTop - cardH * 0.48);
      pen.text(tx, ty, word, charFont, charSize, style.char);

      // english (bottom, first sense, wrapped)
      const eng = (englishes[gi] ?? "").split(";")[0]?.trim() ?? "";
      if (eng) {
        const lines = wrapText(eng, pinyinFont, engSize, cardW * 0.88, 2);
        lines.forEach((ln, li) => {
          const w = pinyinFont.widthOfTextAtSize(ln, engSize);
          pen.text(cxc - w / 2, yTop - cardH * 0.8 - li * engSize * 1.25, ln, pinyinFont, engSize, style.pinyinText);
        });
      }
    }
  }
}

// --- Layout: strokes (progressive stroke-order diagram) --------------------
// Hanzi Writer paths live in a 1024 box with y pointing up (font coords,
// y in [-124, 900]). Flip every y to SVG's y-down convention so pdf-lib's
// drawSvgPath (page = origin + scale * (X, -Y)) places the glyph upright.
function hwPathToSvg(path: string): string {
  let n = -1; // running index over the x,y coordinate stream
  return path.replace(/-?\d*\.?\d+/g, (num) => {
    n += 1;
    return n % 2 === 1 ? String(900 - parseFloat(num)) : num;
  });
}

function renderStrokes(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
  _englishes: string[],
  strokes: Map<string, StrokeData | null>,
  cfg: Config,
  charFont: PDFFont,
  pinyinFont: PDFFont,
  style: Style,
): void {
  const [pageW, pageH] = A4;
  const margin = mm(cfg.marginMm);
  const inner = mm(5);
  const cols = Math.max(1, cfg.cols);
  const cellW = (pageW - 2 * margin - 2 * inner) / cols;
  const cellH = cellW;
  const box = cellW * 0.9;
  const pad = (cellW - box) / 2;
  const lineW = mm(0.13);
  const borderW = mm(0.25);
  const dash: [number, number] = [Math.max(mm(1.3), box / 28), Math.max(mm(0.9), box / 44)];
  const scale = box / 1024;
  const labelSize = mm(3);
  const labelH = mm(5);

  // One block per character: a label row + enough cell rows for its strokes.
  type Row = { type: "label"; gi: number } | { type: "cells"; gi: number; start: number; count: number };
  const rows: Row[] = [];
  for (let gi = 0; gi < chars.length; gi++) {
    const sd = strokes.get(chars[gi]!);
    const total = sd && sd.strokes.length ? sd.strokes.length : 1;
    rows.push({ type: "label", gi });
    for (let s = 0; s < total; s += cols) rows.push({ type: "cells", gi, start: s, count: Math.min(cols, total - s) });
  }

  let page = doc.addPage(A4);
  let pn = new Pen(page, [1, 0, 0, 1, 0, 0]);
  let yCursor = pageH - margin;
  const ensure = (h: number): void => {
    if (yCursor - h < margin) {
      page = doc.addPage(A4);
      pn = new Pen(page, [1, 0, 0, 1, 0, 0]);
      yCursor = pageH - margin;
    }
  };

  for (const row of rows) {
    if (row.type === "label") {
      ensure(labelH);
      const ch = chars[row.gi]!;
      const reading = readings[row.gi] ?? "";
      pn.text(margin, yCursor - labelSize, ch, charFont, labelSize, style.char);
      const cw = charFont.widthOfTextAtSize(ch, labelSize);
      if (reading) pn.text(margin + cw + mm(2), yCursor - labelSize, reading, pinyinFont, labelSize, style.pinyinText);
      yCursor -= labelH;
      continue;
    }
    ensure(cellH);
    const sd = strokes.get(chars[row.gi]!);
    for (let i = 0; i < row.count; i++) {
      const k = row.start + i;
      const boxLeft = margin + inner + i * cellW;
      const boxTop = yCursor - pad;
      const boxBottom = boxTop - box;
      drawMizige(pn, boxLeft, boxBottom, box, "", charFont, 0, style.char, style, lineW, borderW, dash);
      if (sd && sd.strokes.length) {
        for (let s = 0; s <= k; s++) {
          const color = s === k ? style.char : style.trace;
          page.drawSvgPath(hwPathToSvg(sd.strokes[s]!), { x: boxLeft, y: boxTop, scale, color: rgb(...color) });
        }
      } else {
        // no stroke data: fall back to the plain character
        const [tx, ty] = centered(charFont, box * 0.8, chars[row.gi]!, boxLeft + box / 2, boxBottom + box / 2);
        pn.text(tx, ty, chars[row.gi]!, charFont, box * 0.8, style.char);
      }
    }
    yCursor -= cellH;
  }
}

const RENDERERS: Record<Config["layout"], typeof renderStrokes> = {
  big: renderBig,
  grid: renderGrid,
  vocab: renderVocab,
  strokes: renderStrokes,
};

/** Build a vector PDF (Uint8Array) for the given entries. */
export async function buildPdf(
  entries: Entry[],
  cfg: Config,
  assets: Assets,
  style: Style = DEFAULT_STYLE,
): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  doc.registerFontkit(fontkit);
  const charFont = await doc.embedFont(assets.charFont, { subset: true });
  const pinyinFont = await doc.embedFont(assets.pinyinFont, { subset: true });

  const chars = entries.map((e) => e.char);
  const readings = entries.map((e) => resolvePinyin(e.char, e.override, assets.dict));
  const englishes = entries.map((e) => resolveEnglish(e.char, assets.dict));

  const strokeMap = new Map<string, StrokeData | null>();
  if (cfg.layout === "strokes" && assets.loadStrokes) {
    const uniq = [...new Set(chars)];
    const loaded = await Promise.all(uniq.map((c) => assets.loadStrokes!(c)));
    uniq.forEach((c, i) => strokeMap.set(c, loaded[i]!));
  }

  RENDERERS[cfg.layout](doc, chars, readings, englishes, strokeMap, cfg, charFont, pinyinFont, style);
  doc.setTitle(cfg.title || "Chinese character practice cards");
  doc.setCreator("chinese-card-maker");
  return doc.save();
}
