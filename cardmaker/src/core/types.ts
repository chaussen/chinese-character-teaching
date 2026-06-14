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

export type Layout = "big" | "grid" | "vocab";

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

export const DEFAULT_STYLE: Style = {
  grid: [0.67, 0.67, 0.67],
  border: [0.35, 0.35, 0.35],
  pinyinLines: [0.71, 0.71, 0.71],
  pinyinText: [0.16, 0.16, 0.16],
  char: [0.06, 0.06, 0.06],
  trace: [0.75, 0.75, 0.75],
  cut: [0.55, 0.55, 0.55],
};

export const DEFAULT_CONFIG: Config = {
  layout: "big",
  marginMm: 7,
  cols: 8,
  pinyinRatio: 0.2,
  title: "",
  trace: 0,
};
