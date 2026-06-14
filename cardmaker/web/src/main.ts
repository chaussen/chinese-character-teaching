/// <reference types="vite/client" />
import { buildPdf, parseEntries, DEFAULT_CONFIG } from "../../src/core/index.js";
import type { Assets, CharacterDict, Config } from "../../src/core/index.js";
import dictData from "../../data/characters.json";

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const els = {
  chars: $<HTMLTextAreaElement>("chars"),
  layout: $<HTMLSelectElement>("layout"),
  cols: $<HTMLInputElement>("cols"),
  margin: $<HTMLInputElement>("margin"),
  trace: $<HTMLInputElement>("trace"),
  title: $<HTMLInputElement>("title"),
  generate: $<HTMLButtonElement>("generate"),
  download: $<HTMLButtonElement>("download"),
  status: $<HTMLDivElement>("status"),
  meta: $<HTMLSpanElement>("meta"),
  frame: $<HTMLIFrameElement>("frame"),
};

let assetsPromise: Promise<Assets> | null = null;
let currentUrl: string | null = null;
let currentBlob: Blob | null = null;

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
      };
    })();
  }
  return assetsPromise;
}

function readConfig(): Config {
  const layout = els.layout.value === "grid" ? "grid" : "big";
  return {
    ...DEFAULT_CONFIG,
    layout,
    cols: Math.max(1, parseInt(els.cols.value, 10) || 8),
    marginMm: parseFloat(els.margin.value) || 7,
    trace: Math.max(0, parseInt(els.trace.value, 10) || 0),
    title: els.title.value.trim(),
  };
}

function setStatus(msg: string, warn = false): void {
  els.status.textContent = msg;
  els.status.classList.toggle("warn", warn);
}

async function generate(): Promise<void> {
  const { entries, dropped } = parseEntries(els.chars.value);
  if (!entries.length) {
    setStatus("Enter at least one Chinese character.", true);
    return;
  }
  els.generate.disabled = true;
  setStatus("Rendering…");
  try {
    const assets = await loadAssets();
    const cfg = readConfig();
    const bytes = await buildPdf(entries, cfg, assets);
    const blob = new Blob([bytes as BlobPart], { type: "application/pdf" });

    if (currentUrl) URL.revokeObjectURL(currentUrl);
    currentUrl = URL.createObjectURL(blob);
    currentBlob = blob;
    els.frame.src = currentUrl;
    els.download.disabled = false;

    const kb = (blob.size / 1024).toFixed(0);
    els.meta.textContent = `${entries.length} characters · ${cfg.layout} · ${kb} KB`;
    setStatus(dropped.length ? `Skipped ${dropped.length} unsupported character(s): ${dropped.join("")}` : "Ready.", dropped.length > 0);
  } catch (err) {
    console.error(err);
    setStatus(`Render failed: ${(err as Error).message}`, true);
  } finally {
    els.generate.disabled = false;
  }
}

function download(): void {
  if (!currentBlob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(currentBlob);
  a.download = (els.title.value.trim() || "character_cards").replace(/\s+/g, "_") + ".pdf";
  a.click();
  URL.revokeObjectURL(a.href);
}

els.generate.addEventListener("click", generate);
els.download.addEventListener("click", download);
els.layout.addEventListener("change", () => {
  els.cols.disabled = els.layout.value !== "grid";
});

// First render on load.
els.cols.disabled = els.layout.value !== "grid";
generate();
