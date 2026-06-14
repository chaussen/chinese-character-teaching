import { pinyin as pinyinPro } from "pinyin-pro";
import type { CharacterDict, Entry } from "./types.js";

// Tone-mark vowels, indexed [tone][vowel] where vowel order is a o e i u ü.
const TONE_MARKS: Record<number, string> = {
  0: "aoeiuü",
  1: "āōēīūǖ",
  2: "áóéíúǘ",
  3: "ǎǒěǐǔǚ",
  4: "àòèìùǜ",
};

/**
 * Convert numbered pinyin (zhong4, lu:3) to tone-marked pinyin (zhòng, lǚ).
 * Faithful port of the original decode_pinyin; tone marks pass through unchanged.
 */
export function decodePinyin(input: string): string {
  const s = input.toLowerCase();
  let r = "";
  let t = "";
  for (const c of s) {
    if (c >= "a" && c <= "z") {
      t += c;
    } else if (c === ":") {
      // trailing 'u' -> ü
      t = t.slice(0, -1) + "ü";
    } else {
      if (c >= "0" && c <= "5") {
        const tone = parseInt(c, 10) % 5;
        if (tone !== 0) {
          const m = t.match(/[aoeiuü]+/);
          if (m === null) {
            t += c;
          } else if (m[0].length === 1) {
            const pos = TONE_MARKS[0]!.indexOf(m[0]);
            t = t.slice(0, m.index!) + TONE_MARKS[tone]![pos] + t.slice(m.index! + 1);
          } else if (t.includes("a")) {
            t = t.replace("a", TONE_MARKS[tone]![0]!);
          } else if (t.includes("o")) {
            t = t.replace("o", TONE_MARKS[tone]![1]!);
          } else if (t.includes("e")) {
            t = t.replace("e", TONE_MARKS[tone]![2]!);
          } else if (t.endsWith("ui")) {
            t = t.replace("i", TONE_MARKS[tone]![3]!);
          } else if (t.endsWith("iu")) {
            t = t.replace("u", TONE_MARKS[tone]![4]!);
          }
        }
      }
      r += t;
      t = "";
    }
  }
  return r + t;
}

/** CJK Unified Ideographs + Ext-A (covers the curriculum and most rare chars). */
export function isHan(ch: string): boolean {
  const cp = ch.codePointAt(0);
  if (cp === undefined) return false;
  return (
    (cp >= 0x4e00 && cp <= 0x9fff) || // CJK Unified
    (cp >= 0x3400 && cp <= 0x4dbf) || // Ext-A
    (cp >= 0xf900 && cp <= 0xfaff) // Compatibility Ideographs
  );
}

/**
 * Parse free text into entries. A character may carry an inline reading in
 * (half- or full-width) parentheses, e.g. 重(zhòng) or 重(zhong4). Non-Han is
 * skipped. Characters dropped because they're outside the Han range are
 * collected in `dropped` so callers can warn instead of silently losing them.
 */
export function parseEntries(raw: string): { entries: Entry[]; dropped: string[] } {
  const chars = Array.from(raw);
  const entries: Entry[] = [];
  const dropped: string[] = [];
  let i = 0;
  while (i < chars.length) {
    const ch = chars[i]!;
    // A CJK-looking glyph outside our accepted range: record and skip.
    if (!isHan(ch)) {
      if (/\p{Script=Han}/u.test(ch)) dropped.push(ch);
      i += 1;
      continue;
    }
    let j = i + 1;
    let override: string | null = null;
    let k = j;
    while (k < chars.length && (chars[k] === " " || chars[k] === "\t")) k += 1;
    if (k < chars.length && (chars[k] === "(" || chars[k] === "（")) {
      let end = k + 1;
      while (end < chars.length && chars[end] !== ")" && chars[end] !== "）") end += 1;
      override = chars.slice(k + 1, end).join("").trim() || null;
      j = end + 1;
    }
    entries.push({ char: ch, override });
    i = j;
  }
  return { entries, dropped };
}

/** Accept tone marks as-is; convert numbered readings to tone marks. */
export function normalizePinyin(text: string): string {
  if (/\d/.test(text)) {
    return text
      .split(/\s+/)
      .map((tok) => decodePinyin(tok))
      .join("");
  }
  return text;
}

/**
 * Resolve a reading: inline override -> curated dictionary -> pinyin-pro.
 * pinyin-pro picks the most common / contextual reading for 多音字.
 */
export function resolvePinyin(char: string, override: string | null, dict: CharacterDict): string {
  if (override) return normalizePinyin(override);
  const entry = dict[char];
  if (entry && entry.pinyin) return entry.pinyin;
  return pinyinPro(char, { toneType: "symbol", type: "string" });
}
