import { PDFDocument, PDFFont, PDFPage, rgb, degrees } from "pdf-lib";
import fontkit from "@pdf-lib/fontkit";
import type { CharacterDict, Config, Entry, Rgb, Style } from "./types.js";
import { DEFAULT_STYLE } from "./types.js";
import { resolvePinyin } from "./pinyin.js";

/** Fonts + curated dictionary the renderer needs, supplied by the host. */
export interface Assets {
  charFont: Uint8Array;
  pinyinFont: Uint8Array;
  dict: CharacterDict;
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
): void {
  const pad = height * 0.12;
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

function drawCutLine(page: PDFPage, pageW: number, margin: number, y: number, font: PDFFont, style: Style): void {
  page.drawLine({
    start: { x: margin / 2, y },
    end: { x: pageW - margin / 2, y },
    thickness: 1,
    color: rgb(...style.cut),
    dashArray: [mm(1.8), mm(1.3)],
  });
  const label = "✂ cut";
  const size = mm(3.2);
  const w = font.widthOfTextAtSize(label, size);
  page.drawText(label, { x: pageW - margin / 2 - w, y: y + mm(1), size, font, color: rgb(...style.cut) });
}

// --- Layout: big (two rotated characters per page) -------------------------
function renderBig(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
  cfg: Config,
  charFont: PDFFont,
  pinyinFont: PDFFont,
  style: Style,
): void {
  const [pageW, pageH] = A4;
  const margin = mm(cfg.marginMm);
  const sidePad = mm(2.5);
  const usableW = pageW - 2 * margin;
  const halfH = (pageH - 2 * margin) / 2;

  const box = halfH - 2 * sidePad - mm(0.5);
  const pinyinH = box * cfg.pinyinRatio;
  const midGap = Math.max(mm(2), sidePad * 0.5);
  const wc = box + 2 * sidePad;
  const hc = 2 * sidePad + box + midGap + pinyinH;

  const lineW = mm(0.18);
  const borderW = mm(0.4);
  const dash: [number, number] = [Math.max(mm(2), box / 38), Math.max(mm(1.2), box / 60)];
  const charSize = box * 0.82;
  const pinyinSize = pinyinH * 0.5;
  const labelFont = pinyinFont;

  const pages = Math.max(1, Math.ceil(chars.length / 2));
  for (let p = 0; p < pages; p++) {
    const page = doc.addPage(A4);
    for (let slot = 0; slot < 2; slot++) {
      const gi = p * 2 + slot;
      if (gi >= chars.length) continue;
      const regionBottom = margin + (1 - slot) * halfH; // slot 0 = top
      const ex = margin + (usableW - hc) / 2;
      const ey = regionBottom + (halfH - wc) / 2;
      // rotate 90deg CCW then translate so the card bbox sits at (ex, ey)
      const pen = new Pen(page, [0, 1, -1, 0, ex + hc, ey]);
      const boxBottom = sidePad;
      // trace mode on the big card: render the character faint to be traced over.
      const charColor = cfg.trace > 0 ? style.trace : style.char;
      drawMizige(pen, sidePad, boxBottom, box, chars[gi]!, charFont, charSize, charColor, style, lineW, borderW, dash);
      const pinyinBottom = boxBottom + box + midGap;
      drawPinyinGuide(pen, sidePad, sidePad + box, pinyinBottom, pinyinH, readings[gi]!, pinyinFont, pinyinSize, style, lineW, dash);
    }
    drawCutLine(page, pageW, margin, margin + halfH, labelFont, style);
  }
}

// --- Layout: grid (many small cells per page) ------------------------------
function renderGrid(
  doc: PDFDocument,
  chars: string[],
  readings: string[],
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
      drawCutLine(page, pageW, margin, margin + halfH, pinyinFont, style);
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
    drawCutLine(page, pageW, margin, margin + halfH, pinyinFont, style);
  }
}

const RENDERERS: Record<Config["layout"], typeof renderBig> = {
  big: renderBig,
  grid: renderGrid,
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

  RENDERERS[cfg.layout](doc, chars, readings, cfg, charFont, pinyinFont, style);
  doc.setTitle(cfg.title || "Chinese character practice cards");
  doc.setCreator("chinese-card-maker");
  return doc.save();
}
