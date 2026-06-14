#!/usr/bin/env node
/**
 * Batch / one-shot PDF generator. Mirrors the old worksheet_maker CLI but emits
 * tiny vector PDFs.
 *
 *   tsx src/cli.ts 花 园 门 前
 *   tsx src/cli.ts --file ../worksheets/yr1_chars.txt
 *   tsx src/cli.ts --batch ../worksheets --layout grid
 */
import { readFile, writeFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join, basename, extname } from "node:path";
import { parseArgs } from "node:util";
import { createRequire } from "node:module";
import { buildPdf, parseEntries, parseWords, DEFAULT_CONFIG, type Assets, type Config, type StrokeData } from "./core/index.js";

const require = createRequire(import.meta.url);
async function loadStrokes(char: string): Promise<StrokeData | null> {
  try {
    return require(`hanzi-writer-data/${char}.json`) as StrokeData;
  } catch {
    return null;
  }
}

const here = dirname(fileURLToPath(import.meta.url));
const pkgRoot = join(here, "..");

async function loadAssets(): Promise<Assets> {
  const [charFont, pinyinFont, dictRaw] = await Promise.all([
    readFile(join(pkgRoot, "fonts", "char.ttf")),
    readFile(join(pkgRoot, "fonts", "pinyin.ttf")),
    readFile(join(pkgRoot, "data", "characters.json"), "utf8"),
  ]);
  return { charFont, pinyinFont, dict: JSON.parse(dictRaw), loadStrokes };
}

/** yr1_chars.txt -> yr1_character_cards */
function deriveName(inputPath: string): string {
  let base = basename(inputPath, extname(inputPath));
  if (base.endsWith("_chars")) base = base.slice(0, -"_chars".length);
  return `${base}_character_cards`;
}

async function generate(raw: string, outPrefix: string, cfg: Config, assets: Assets): Promise<number> {
  const { entries, dropped } = cfg.layout === "vocab" ? parseWords(raw) : parseEntries(raw);
  if (dropped.length) console.warn(`  ! skipped ${dropped.length} unsupported char(s): ${dropped.join("")}`);
  if (!entries.length) {
    console.error("No characters provided.");
    return 0;
  }
  const pdf = await buildPdf(entries, cfg, assets);
  await writeFile(`${outPrefix}.pdf`, pdf);
  return entries.length;
}

async function main(): Promise<number> {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      chars: { type: "string", default: "" },
      file: { type: "string" },
      batch: { type: "string" },
      out: { type: "string" },
      outdir: { type: "string" },
      layout: { type: "string", default: "big" },
      cols: { type: "string" },
      "margin-mm": { type: "string", default: "7" },
      trace: { type: "string", default: "0" },
      title: { type: "string", default: "" },
    },
  });

  const layout =
    values.layout === "grid" || values.layout === "vocab" || values.layout === "strokes" ? values.layout : "big";
  const cfg: Config = {
    ...DEFAULT_CONFIG,
    layout,
    cols: values.cols ? parseInt(values.cols, 10) : layout === "vocab" ? 3 : 8,
    marginMm: parseFloat(values["margin-mm"]!),
    trace: parseInt(values.trace!, 10) || 0,
    title: values.title!,
  };
  const assets = await loadAssets();

  if (values.batch) {
    const dir = values.batch;
    const all = await readdir(dir);
    const files = all.filter((f) => f.endsWith("_chars.txt")).sort();
    const list = (files.length ? files : all.filter((f) => f.endsWith(".txt")).sort()).map((f) => join(dir, f));
    if (!list.length) {
      console.error(`No .txt lists found in ${dir}`);
      return 1;
    }
    const outdir = values.outdir ?? dir;
    for (const path of list) {
      const raw = await readFile(path, "utf8");
      const prefix = join(outdir, deriveName(path));
      const n = await generate(raw, prefix, cfg, assets);
      if (n) console.log(`${basename(path).padEnd(20)} -> ${prefix}.pdf  (${n} chars)`);
    }
    return 0;
  }

  let raw = [...positionals, values.chars].join(" ");
  let srcPath: string | null = null;
  if (values.file) {
    raw += " " + (await readFile(values.file, "utf8"));
    srcPath = values.file;
  }

  let prefix: string;
  if (values.out) prefix = values.out;
  else if (srcPath) prefix = join(values.outdir ?? dirname(srcPath) ?? ".", deriveName(srcPath));
  else prefix = join(values.outdir ?? ".", "worksheet");

  const n = await generate(raw, prefix, cfg, assets);
  if (n) console.log(`${n} characters -> ${prefix}.pdf`);
  return 0;
}

main().then((code) => process.exit(code));
