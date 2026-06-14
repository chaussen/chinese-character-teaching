# Card Maker — Architecture & Code Assessment

**Date:** 2026-06-14
**Scope:** `chinese_tools/cards/` (the "card maker") and its direct dependencies
(`data/pinyin_data.py`, `settings.py`, `paths.py`, `ui/app.py`, `fonts/`).
**Goal of the review:** assess the tool as a legacy codebase and lay out a
systematic path to revive it for broader usage and extended functionality.

---

## 1. What "the card maker" actually is

The `cards/` package contains **two different generations of the same idea**,
and the distinction drives every recommendation below:

| File | Born | Status | What it does |
|------|------|--------|--------------|
| `flashcard_maker.py` (`ChineseCardMaker`) | 2020 | **Legacy, broken** | Per-character JPG flashcards + pinyin-header cards, driven only from the Tkinter UI. |
| `worksheet_maker.py` | 2024+ | **Active, healthy** | A4 print-ready PDFs: 米字格 + 四线三格 pinyin guide, `big`/`grid` layouts, batch mode, 多音字 overrides. README's "main tool". |

They overlap conceptually (both draw a character in a grid with pinyin) but
share **no code**. The grid-drawing logic exists twice, in incompatible forms.
The modern tool quietly superseded the old one, but the old one was never
retired — it is still the only thing the GUI knows how to call.

**Headline finding:** the named, original "card maker" (`ChineseCardMaker`) **no
longer runs at all** on a current environment, while the capable replacement
(`worksheet_maker`) has **no GUI and isn't installable** — so neither is in a
state to reach a broader (non-developer, teacher) audience today.

---

## 2. Critical issues (must fix to "revive")

### C1. Legacy flashcard maker is dead on modern Pillow
`ChineseCardMaker` calls the removed `ImageFont.getsize()` /
`font.font.getsize()` API in four places
(`flashcard_maker.py:47, 90, 102, 135-136`). `getsize` was deprecated in
Pillow 9.2 and **removed in Pillow 10 (2023)**. The repo runs on Pillow 12
today, so every entry point of this class raises `AttributeError` before
producing an image. It is untested (no test references it) and therefore the
breakage is silent.

**Impact:** the tool the user calls "the card maker" is 100% non-functional.
Reviving it means either porting it to `getbbox()`/`getlength()` or — better —
folding its one unique capability (single-character image export) into
`worksheet_maker` and deleting it.

### C2. `requirements.txt` does not describe the project
The file is the stock pip *example template* (comments about
`--use-feature=2020-resolver`, "Requirements without Version Specifiers")
carried over verbatim. It pins `Pillow==8.0.0`, `pinyin==0.4.0`,
`robotframework`, `buildconfig`, `certifi`, `urllib3`… — most unused, all stale,
and the Pillow pin is **four major versions behind** what the code needs.
Anyone installing from it gets a broken environment.

### C3. The only GUI wires the broken tool and dead external services
`ui/app.py` is effectively abandonware:
- It executes on **import** — module-level `tk.Tk()` + `mainloop()`
  (`ui/app.py:226-230`) — so simply importing the module pops a window.
- Hardcoded Windows-only paths: `C:/Users/jni/apps/flashplayer.exe`
  (`ui/app.py:15`).
- "Stroke order" launches **Adobe Flash** against a `yes-chinese.com` `.swf`
  (`ui/app.py:16, 114-118`). Flash has been **end-of-life since Dec 2020**;
  this feature cannot work.
- It calls the broken `ChineseCardMaker`, not `worksheet_maker`.

For "broader usage" this is the single biggest gap: the audience is teachers,
and the front door is a non-portable, half-dead Tk window bound to the wrong
engine.

---

## 3. Functional assessment

### What works well (worksheet_maker)
- Correct, idiomatic pinyin resolution chain: inline override → curated
  `pinyin_data` reading → `xpinyin` fallback (`worksheet_maker.py:174-180`).
- 多音字 handling via `字(pinyin)` / `字(pin1yin1)` parsing
  (`parse_entries`, `normalize_pinyin`) — genuinely useful and tested.
- Two real layouts (`big`, `grid`) dispatched cleanly through a `RENDERERS`
  table; batch mode over a folder; sensible output naming (`derive_name`).
- Proper teaching geometry: 米字格 with dashed cross + diagonals, and a real
  四线三格 four-line guide with the pinyin seated on the third line.

### Functional gaps (to extend)
1. **No tracing / stroke practice.** Practice sheets normally include faint
   "trace-me" glyphs and several blank repeat boxes per character. Today every
   box is either a solid character or empty — there's no graded-fade or
   repeat-N-times mode. This is the most-requested feature for the use case.
2. **No stroke-order rendering.** The old UI gestured at it (via dead Flash);
   nothing renders stroke order now. A modern approach (Hanzi Writer data,
   or a stroke-order font) would be a marquee feature.
3. **No sheet metadata.** `Config.title` exists (`worksheet_maker.py:111`) but
   is never drawn, and there's no name/date/class header line — basic for
   classroom handouts.
4. **No selection/ordering control.** No dedup, no shuffle, no "N per page",
   no range selection from a larger list.
5. **Han detection is BMP-only.** `is_han` accepts U+4E00–U+9FFF
   (`worksheet_maker.py:133-134`) and silently drops CJK Ext-A/B and rarer
   characters — they vanish from the sheet with no warning.
6. **English/meaning is unused here.** `pinyin_data` carries rich glosses but
   cards never surface them; a "vocab card" mode (char + pinyin + English) is
   low-hanging fruit and overlaps the legacy maker's intent.
7. **Single character font.** No 楷体/Kaiti ships, so the default GB2312 face —
   a print style — is what every sheet uses despite the README suggesting
   otherwise. Handwriting practice ideally uses a Kai/regular-script face.

---

## 4. Non-functional assessment

### N1. Output is heavy raster, not vector
`save_pdf` rasterizes each full A4 page to 300-DPI grayscale and embeds it as an
image (`worksheet_maker.py:355-366`). Consequences:
- The committed PDFs are **18–22 MB each (~120 MB total in `worksheets/`)**.
- Characters are bitmaps: not crisp at print scale, not selectable, not
  re-flowable, and balloon the git history.

A vector PDF backend (e.g. `reportlab`, drawing text + lines directly) would
produce **tens of KB**, sharper print output, and real glyphs — a major win for
both quality and "email it to a teacher" distribution.

### N2. Not installable / not packaged
There is no `pyproject.toml`. The only documented way to run anything is
`python -m chinese_tools…` from the repo root (`README`). No `pip install .`, no
`console_scripts` (`worksheet-maker …`), no version. This is a real adoption
barrier for non-developers.

### N3. Pinyin font is found by guessing, and not bundled
`find_pinyin_font` probes a hardcoded list of OS font paths and **raises** if
none exist (`worksheet_maker.py:77-84`). The char font is bundled but the
*pinyin* font is not — so the tool's output isn't reproducible across machines,
and a clean CI box (or container) would fail at render time. The 5 passing tests
only survive because the test host happens to have DejaVu.

### N4. Font licensing unverified
`fonts/GB2312.ttf` (4 MB) is redistributed with the repo with no stated license.
"Broader usage" = redistribution; this needs to be confirmed/replaced with a
clearly-licensed open font (e.g. an OFL Kaiti).

### N5. Large binaries tracked in git
The generated PDFs live in version control. They should be build artifacts
(CI release assets), not committed blobs, to keep the repo clone-able.

---

## 5. Code-quality assessment

**worksheet_maker.py — good, with rough edges**
- Clean structure: `Style`/`Config` dataclasses, mm→px helper, pure render
  functions, dispatch table. Readable and largely well-documented.
- Dead/!wired config: `Config.title` and `Config.pinyin_ratio` are not all
  exposed as CLI flags, and `title` is never used. Trim or wire them.
- `render_big` / `render_grid` duplicate a lot of setup (font sizing, dash/gap,
  reading resolution, page loop). A shared helper would cut ~40 lines.
- Tests assert only "file exists" + page count; no check that the right number
  of cells/characters were drawn, or that overrides reach the page.

**flashcard_maker.py — legacy smells throughout**
- `from chinese_tools.settings import *` (`:6`) — wildcard import; all layout is
  module-global constants, so nothing is configurable per call.
- Debug `print()` as control flow / output (`:100, 137-138, 172, 183, 189`);
  `print_character_pinyin` even prints dict-literal lines — it was a one-off
  scaffold for hand-building `pinyin_data`, not production code.
- `print_character_pinyin` returns a value **and** prints **and** has side
  effects; `add_pinyin_header` mixes layout math, drawing, and file I/O.
- Grid-drawing duplicated (`initialize_character_card` vs `add_pinyin_header`).
- Lossy **JPG** output for line art (artifacts on thin grid lines).
- No `__main__`/CLI; only reachable from the broken GUI.

**Shared/data**
- `pinyin_data.py` has a literal `# DO NOT TOUCH THE CODE BELOW!` banner around
  `decode_pinyin` — a smell; that tone-decoder is reusable and should be a
  small, tested module (it already has one test).
- Curated map (`CHARACTER_PINYIN_ENGLISH_MAPPING`) and `character_dict.py`
  duplicate the same entries; single source of truth needed.

---

## 6. Systematic recommendations

Prioritized; each item tagged **[Func] / [Non-func] / [Quality]**.

### Phase 0 — Stop the bleeding (small, high value)
1. **[Non-func]** Replace `requirements.txt` with an accurate set and add a
   `pyproject.toml` (deps: `Pillow`, `xpinyin`; optional extras for kahoot/game).
   Add `console_scripts` so `worksheet-maker` is a real command. *(C2, N2)*
2. **[Quality]** Decide the legacy story explicitly. Recommended: **port the one
   unique feature** (single-character image export) into `worksheet_maker` as a
   `--per-char-images` option, then **delete `flashcard_maker.py`** and the dead
   `ui/app.py`. If kept, port `getsize→getbbox` first so it at least runs. *(C1, C3)*
3. **[Non-func]** Bundle a clearly-licensed pinyin font (or embed DejaVu) so
   render never depends on host fonts; make `find_pinyin_font` fall back to the
   bundled file instead of raising. *(N3)*
4. **[Non-func]** Stop committing generated PDFs; move them to CI release
   artifacts and `.gitignore` them. *(N5)*

### Phase 1 — Quality & confidence
5. **[Quality]** Factor the shared render setup out of `render_big`/`render_grid`;
   delete unused `Config` fields. 
6. **[Quality]** Strengthen tests: assert characters-per-page, that overrides
   render, that missing pinyin font falls back, and add a golden-image
   (perceptual) test for one small sheet.
7. **[Quality]** Single source of truth for character data; make `decode_pinyin`
   a small importable, tested module (drop the "DO NOT TOUCH" banner).
8. **[Func]** Widen `is_han` to cover CJK Ext-A/B (and warn on dropped chars).

### Phase 2 — Functionality for broader usage
9. **[Func]** **Tracing / repeat mode**: faint trace glyphs + N blank repeat
   boxes per character (the top requested feature for handwriting practice).
10. **[Func]** **Sheet header**: wire `--title` + an optional name/date/class
    line for classroom handouts.
11. **[Func]** **Vocab-card mode**: char + pinyin + English gloss (reuses
    `pinyin_data`), absorbing the legacy maker's intent.
12. **[Func]** Ship a **Kaiti/楷体** open font as the practice default.
13. **[Non-func]** **Vector PDF backend** (reportlab) — KB-sized, crisp, real
    glyphs — alongside or replacing the raster path. *(N1)*

### Phase 3 — Reach (the actual "broader usage")
14. **[Func/Non-func]** A modern front end to replace the dead Tk GUI. Best
    fit: a small **web app** (paste characters → preview → download PDF), which
    a teacher can use with zero install. A thin Streamlit/Flask layer over the
    existing pure render functions is enough to start.
15. **[Func]** Stroke-order rendering (Hanzi Writer data or a stroke-order font)
    — the long-promised feature, finally without Flash.

---

## 7. Suggested target architecture

```
chinese_tools/cards/
  model.py        # Entry, Config, Style dataclasses (pure data)
  pinyin.py       # resolve_pinyin, decode_pinyin, parse_entries (tested)
  render.py       # pure draw_* primitives + layouts (no I/O)
  backends/
    raster.py     # current Pillow path
    vector.py     # reportlab path (new)
  cli.py          # argparse → build()  (console_script: worksheet-maker)
fonts/            # bundled char + pinyin fonts, licensed
web/              # optional Streamlit/Flask front end over render.py
```

Keep render pure (no printing, no file writes); push I/O to the edges (CLI/web).
This makes the same engine drive CLI, web, and tests — the precondition for
both broader usage and extended functionality.

---

## 8. One-paragraph verdict

`worksheet_maker.py` is a solid, modern core worth investing in; the legacy
`ChineseCardMaker` and Tk GUI are dead weight (broken on current Pillow, bound
to EOL Flash) and should be retired rather than repaired. The fastest route to
"revive for broader usage" is **not** more drawing code — it's packaging
(installable + accurate deps + bundled fonts), a vector PDF backend to fix
output weight/quality, and a zero-install web front end over the existing pure
render functions. With those in place, the high-value teaching features
(tracing, headers, vocab mode, stroke order) slot in cleanly on top.
</content>
</invoke>
