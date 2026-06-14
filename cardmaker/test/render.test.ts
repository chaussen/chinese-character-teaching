import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PDFDocument } from "pdf-lib";
import { buildPdf, parseEntries, parseWords, resolveEnglish, decodePinyin, resolvePinyin, isHan, DEFAULT_CONFIG } from "../src/core/index.js";
import type { Assets, CharacterDict } from "../src/core/index.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dict: CharacterDict = JSON.parse(readFileSync(join(root, "data", "characters.json"), "utf8"));
const assets: Assets = {
  charFont: readFileSync(join(root, "fonts", "char.ttf")),
  pinyinFont: readFileSync(join(root, "fonts", "pinyin.ttf")),
  dict,
};

describe("pinyin", () => {
  it("decodes numbered pinyin to tone marks", () => {
    expect(decodePinyin("zhong4")).toBe("zhòng");
    expect(decodePinyin("hang2")).toBe("háng");
    expect(decodePinyin("lu:3")).toBe("lǚ");
  });

  it("parses han and inline overrides, full-width parens too", () => {
    const { entries } = parseEntries("学习 重(zhòng) 行（hang2）");
    expect(entries.map((e) => e.char)).toEqual(["学", "习", "重", "行"]);
    expect(entries.find((e) => e.char === "重")?.override).toBe("zhòng");
    expect(entries.find((e) => e.char === "行")?.override).toBe("hang2");
  });

  it("ignores non-han", () => {
    const { entries } = parseEntries("a1 b2 -- 你 好!");
    expect(entries.map((e) => e.char)).toEqual(["你", "好"]);
  });

  it("override beats default; numbers become marks", () => {
    expect(resolvePinyin("重", "chóng", dict)).toBe("chóng");
    expect(resolvePinyin("行", "hang2", dict)).toBe("háng");
  });

  it("isHan covers Ext-A", () => {
    expect(isHan("㐀")).toBe(true); // U+3400
    expect(isHan("a")).toBe(false);
  });
});

describe("buildPdf", () => {
  it("big layout: 3 chars -> 2 pages, valid small vector PDF", async () => {
    const { entries } = parseEntries("学习重");
    const bytes = await buildPdf(entries, DEFAULT_CONFIG, assets);
    expect(Buffer.from(bytes.slice(0, 5)).toString()).toBe("%PDF-");
    const doc = await PDFDocument.load(bytes);
    expect(doc.getPageCount()).toBe(2);
    expect(bytes.length).toBeLessThan(1_000_000); // vector: well under the old 18MB raster
  });

  it("grid layout: one page for a short list", async () => {
    const { entries } = parseEntries("花园门前个他");
    const bytes = await buildPdf(entries, { ...DEFAULT_CONFIG, layout: "grid" }, assets);
    const doc = await PDFDocument.load(bytes);
    expect(doc.getPageCount()).toBe(1);
  });

  it("grid trace mode builds a valid one-page sheet", async () => {
    const { entries } = parseEntries("花园门前");
    const bytes = await buildPdf(entries, { ...DEFAULT_CONFIG, layout: "grid", trace: 3 }, assets);
    expect(Buffer.from(bytes.slice(0, 5)).toString()).toBe("%PDF-");
    const doc = await PDFDocument.load(bytes);
    expect(doc.getPageCount()).toBe(1);
  });

  it("big trace mode builds (faint character)", async () => {
    const { entries } = parseEntries("学习重");
    const bytes = await buildPdf(entries, { ...DEFAULT_CONFIG, trace: 1 }, assets);
    const doc = await PDFDocument.load(bytes);
    expect(doc.getPageCount()).toBe(2);
  });

  it("vocab layout builds with words + English", async () => {
    const { entries } = parseWords("花园 大门 季节");
    expect(entries.map((e) => e.char)).toEqual(["花园", "大门", "季节"]);
    expect(resolveEnglish("花园", dict)).toBe("garden");
    const bytes = await buildPdf(entries, { ...DEFAULT_CONFIG, layout: "vocab", cols: 3 }, assets);
    expect(Buffer.from(bytes.slice(0, 5)).toString()).toBe("%PDF-");
    expect((await PDFDocument.load(bytes)).getPageCount()).toBe(1);
  });
});

describe("parseWords", () => {
  it("keeps multi-char words, supports inline overrides, drops non-han", () => {
    const { entries, dropped } = parseWords("花园 重(zhòng) hello 季节");
    expect(entries.map((e) => e.char)).toEqual(["花园", "重", "季节"]);
    expect(entries.find((e) => e.char === "重")?.override).toBe("zhòng");
    expect(dropped).toContain("hello");
  });
});
