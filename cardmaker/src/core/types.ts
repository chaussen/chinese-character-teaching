/** A single character to render, plus an optional pinyin override. */
export interface Entry {
  char: string;
  /** Explicit reading: tone marks (zhòng) or numbered (zhong4); null = auto. */
  override: string | null;
}

/** Curated reading + gloss, keyed by character/word. */
export interface DictEntry {
  pinyin: string;
  english: string;
}
export type CharacterDict = Record<string, DictEntry>;

/** RGB in 0..1 (pdf-lib convention). */
export type Rgb = readonly [number, number, number];

export interface Style {
  grid: Rgb; // 米字格 cross + diagonals
  border: Rgb; // 米字格 outer border
  pinyinLines: Rgb; // 四线三格 guide
  pinyinText: Rgb;
  char: Rgb; // solid character
  trace: Rgb; // faint "trace me" character
  cut: Rgb; // cut line + label
}

export type Layout = "big" | "grid" | "vocab" | "strokes";

/** Per-character stroke data (Hanzi Writer / Make Me a Hanzi shape). */
export interface StrokeData {
  strokes: string[];
}

export interface Config {
  layout: Layout;
  marginMm: number;
  /** grid layout: cells per row. */
  cols: number;
  /** pinyin band height relative to the 米字格 box. */
  pinyinRatio: number;
  /** Optional sheet title drawn at the top of each page. */
  title: string;
  /** Trace-then-write: how many faint trace glyphs precede blank practice cells. */
  trace: number;
}

// 米字格 grids are traditionally printed in red: high contrast from a distance,
// distinct in hue from the black character so the two don't visually merge, and
// it still reduces to a clear mid-grey if printed black & white.
export const DEFAULT_STYLE: Style = {
  grid: [0.82, 0.24, 0.22], // 米字格 cross + diagonals — red
  border: [0.7, 0.12, 0.12], // 米字格 outer border — stronger red
  pinyinLines: [0.85, 0.33, 0.3], // 四线三格 guide — red, slightly lighter
  pinyinText: [0, 0, 0], // pinyin solid black for contrast
  char: [0, 0, 0], // character solid black
  trace: [0.72, 0.72, 0.72], // faint trace / earlier strokes
  cut: [0.55, 0.55, 0.55], // cut guide stays neutral grey
};

export const DEFAULT_CONFIG: Config = {
  layout: "big",
  marginMm: 7,
  cols: 8,
  pinyinRatio: 0.2,
  title: "",
  trace: 0,
};
