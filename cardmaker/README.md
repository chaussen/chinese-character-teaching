# chinese-card-maker

A rewrite of the Chinese character practice-card maker as a **TypeScript**
engine that emits **vector** PDFs (KB-sized, crisp, real glyphs) instead of the
old multi-megabyte rasters. One engine drives a Node CLI today and a zero-install
web app (in progress).

Each character sits in a 米字格 (solid border, dashed cross + diagonals) with its
pinyin on top in a 四线三格 four-line guide.

## Layout of the package

```
src/core/        framework-agnostic engine (no file/network I/O)
  types.ts         Config, Style, Entry, dictionary types
  pinyin.ts        parse 字(pinyin) input, numbered->tone-mark, resolve readings
  render.ts        pdf-lib vector renderer (big + grid layouts, affine Pen)
src/cli.ts       Node CLI: single / --file / --batch
web/             zero-install browser app (Vite): paste -> preview -> download
data/            characters.json (curated pinyin + English, migrated)
fonts/           bundled char + pinyin fonts (reproducible output)
test/            vitest suite
```

The core takes its fonts and dictionary as **injected bytes/data**, so the same
code runs in Node (CLI) and the browser (web app) unchanged.

## CLI

```bash
npm install
npx tsx src/cli.ts 花 园 门 前                       # -> ./worksheet.pdf
npx tsx src/cli.ts --file ../worksheets/yr1_chars.txt # -> yr1_character_cards.pdf
npx tsx src/cli.ts --batch ../worksheets --layout big # regenerate a folder
npx tsx src/cli.ts --chars "重(zhòng) 行(háng)"        # 多音字 overrides
npx tsx src/cli.ts --chars "花园 大门 季节" --layout vocab  # word flashcards + English
npx tsx src/cli.ts --chars "我 你 好" --layout strokes      # stroke-order diagram
```

Options: `--layout big|grid|vocab|strokes`, `--cols N`, `--margin-mm N`,
`--trace N`, `--out`, `--outdir`, `--title`, `--char-font PATH`,
`--pinyin-font PATH`. Readings resolve as: inline override → curated dictionary →
`pinyin-pro`.

For authentic handwriting strokes, pass a 楷体/Kaiti TTF via `--char-font` (e.g.
[LXGW WenKai](https://github.com/lxgw/LxgwWenKai)); the web app has a font picker
for the same. fontkit subsets whatever font you give it, so PDFs stay tiny.

`strokes` draws a progressive stroke-order diagram per character (newest stroke
black, earlier strokes grey) from **Hanzi Writer** data — the CLI reads it from
the `hanzi-writer-data` package, the web app fetches it per character from a CDN.

`vocab` makes cut-out flashcards (word + pinyin + English from the curated
dictionary) and parses input as whitespace-separated **words**, so multi-character
词 stay intact.

`--trace N` turns on copy practice: in **grid** each character gets its own row
(`[solid][faint × N][blank…]`); in **big** the large character is drawn faint to
be traced over.

## Web app

```bash
npm run web:dev    # local dev server
npm run web:build  # -> dist-web/ (static, deployable anywhere)
```

The app is client-side only. It deploys to GitHub Pages via
`.github/workflows/deploy-cardmaker.yml` — enable it once under
**repo Settings → Pages → Source: GitHub Actions**.

## Develop

```bash
npm test          # vitest
npm run typecheck # tsc (core + web)
npm run build     # tsc -> dist/
```

## Status

- [x] Core engine: pinyin resolution, both layouts, vector PDF
- [x] Node CLI (single / file / batch) with parity to the old tool
- [x] Web app (paste → preview → download), client-side, + Pages deploy workflow
- [x] Tracing / repeat-box practice mode (grid rows + faint big card)
- [x] Vocab-card mode (word + pinyin + English flashcards)
- [x] Stroke order (Hanzi Writer) — progressive diagram
- [x] Custom character/pinyin fonts (CLI flags + web upload) for Kaiti etc.
- [ ] Retire the dead Python card code
