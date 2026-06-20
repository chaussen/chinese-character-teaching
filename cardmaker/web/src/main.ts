/// <reference types="vite/client" />
import { buildPdf, parseEntries, parseWords, DEFAULT_CONFIG } from "../../src/core/index.js";
import type { Assets, CharacterDict, Config, StrokeData } from "../../src/core/index.js";
import dictData from "../../data/characters.json";

// Stroke data is large (one file per character); fetch on demand from a CDN.
const strokeCache = new Map<string, StrokeData | null>();
async function loadStrokes(char: string): Promise<StrokeData | null> {
  if (strokeCache.has(char)) return strokeCache.get(char)!;
  let data: StrokeData | null = null;
  try {
    const res = await fetch(`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2/${encodeURIComponent(char)}.json`);
    if (res.ok) data = (await res.json()) as StrokeData;
  } catch {
    data = null;
  }
  strokeCache.set(char, data);
  return data;
}

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const els = {
  form: $<HTMLFormElement>("cardForm"),
  chars: $<HTMLTextAreaElement>("chars"),
  layout: $<HTMLSelectElement>("layout"),
  cols: $<HTMLInputElement>("cols"),
  colsField: $<HTMLDivElement>("colsField"),
  margin: $<HTMLInputElement>("margin"),
  trace: $<HTMLInputElement>("trace"),
  traceField: $<HTMLDivElement>("traceField"),
  title: $<HTMLInputElement>("title"),
  charfont: $<HTMLInputElement>("charfont"),
  download: $<HTMLButtonElement>("download"),
  status: $<HTMLParagraphElement>("status"),
};

let assetsPromise: Promise<Assets> | null = null;
let customCharFont: Uint8Array | null = null;

async function loadAssets(): Promise<Assets> {
  if (!assetsPromise) {
    const base = import.meta.env.BASE_URL;
    assetsPromise = (async () => {
      const [charFont, pinyinFont] = await Promise.all([
        fetch(`${base}fonts/char.ttf`).then((r) => r.arrayBuffer()),
        fetch(`${base}fonts/pinyin.ttf`).then((r) => r.arrayBuffer()),
      ]);
      return {
        charFont: new Uint8Array(charFont),
        pinyinFont: new Uint8Array(pinyinFont),
        dict: dictData as CharacterDict,
        loadStrokes,
      };
    })();
  }
  return assetsPromise;
}

function readConfig(): Config {
  const v = els.layout.value;
  const layout = v === "grid" || v === "vocab" || v === "strokes" ? v : "big";
  return {
    ...DEFAULT_CONFIG,
    layout,
    cols: Math.max(1, parseInt(els.cols.value, 10) || (layout === "vocab" ? 3 : 8)),
    marginMm: parseFloat(els.margin.value) || 7,
    trace: Math.max(0, parseInt(els.trace.value, 10) || 0),
    title: els.title.value.trim(),
  };
}

function setStatus(msg: string, level: "info" | "warn" | "error" = "info"): void {
  els.status.textContent = msg;
  els.status.classList.toggle("warn", level === "warn");
  els.status.classList.toggle("error", level === "error");
}

// Each layout only uses a subset of the page-setup fields; hide the rest so the
// form doesn't present knobs that have no effect for the current choice.
function syncFieldVisibility(): void {
  const layout = els.layout.value;
  els.colsField.hidden = !(layout === "grid" || layout === "vocab");
  els.traceField.hidden = !(layout === "big" || layout === "grid");
}

async function downloadCards(): Promise<void> {
  const isVocab = els.layout.value === "vocab";
  const { entries, dropped } = isVocab ? parseWords(els.chars.value) : parseEntries(els.chars.value);
  if (!entries.length) {
    setStatus("Enter at least one Chinese character.", "error");
    els.chars.focus();
    return;
  }

  els.download.disabled = true;
  els.download.setAttribute("aria-busy", "true");
  setStatus("Rendering PDF…");
  try {
    const base = await loadAssets();
    const assets = customCharFont ? { ...base, charFont: customCharFont } : base;
    const cfg = readConfig();
    const bytes = await buildPdf(entries, cfg, assets);
    const blob = new Blob([bytes as BlobPart], { type: "application/pdf" });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (els.title.value.trim() || "character_cards").replace(/\s+/g, "_") + ".pdf";
    a.click();
    URL.revokeObjectURL(url);

    const kb = (blob.size / 1024).toFixed(0);
    const summary = `Downloaded ${entries.length} character${entries.length === 1 ? "" : "s"} · ${cfg.layout} layout · ${kb} KB.`;
    setStatus(dropped.length ? `${summary} Skipped unsupported: ${dropped.join("")}` : summary, dropped.length ? "warn" : "info");
  } catch (err) {
    console.error(err);
    setStatus(`Could not generate the PDF: ${(err as Error).message}`, "error");
  } finally {
    els.download.disabled = false;
    els.download.removeAttribute("aria-busy");
  }
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  void downloadCards();
});
els.charfont.addEventListener("change", async () => {
  const file = els.charfont.files?.[0];
  customCharFont = file ? new Uint8Array(await file.arrayBuffer()) : null;
});
els.layout.addEventListener("change", syncFieldVisibility);

syncFieldVisibility();
