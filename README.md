# Chinese Character Teaching Tools

Tools and web apps for teaching Chinese characters: a browser learning app, a
classical-text reader, print-ready handwriting practice cards (米字格 + pinyin),
vocab flashcards, stroke-order diagrams, a Kahoot quiz-sheet generator, and a
matching game.

## Public site (GitHub Pages)

A static site is assembled and published by GitHub Actions
(`.github/workflows/deploy-pages.yml`). Pages source must be **"GitHub Actions"**
(the legacy Jekyll "deploy from a branch" path is off).

| URL path      | Content                          | Source |
|---------------|----------------------------------|--------|
| `/`           | Landing / hub                    | `landing/` |
| `/studio/`    | Character Studio learning app    | `studio.html` + `learn/` + `audio/` |
| `/cardmaker/` | Card Maker web app               | built from `cardmaker/` |
| `/reader/`    | Classical Reader                 | `classical-reader/index.html` |
| `/history/`   | 史案 History KG Reader            | `history-reader/` |

To work on the Studio locally, serve the repo root and open `studio.html`
(it loads its engine and data from `learn/` and clips from `audio/`).

## Repository layout

```
landing/                  # public landing / hub page (served at /)
studio.html               # Character Studio shell (served at /studio/)
learn/                    # Character Studio engine + data (vanilla JS)
audio/                    # edge-tts recordings (char / word / sentence)
classical-reader/         # Classical Reader app (index.html) + design source
history-reader/           # 史案 history knowledge-graph reader (served at /history/)
tools/                    # content build pipeline + audio generator

cardmaker/                # ← the card maker (TypeScript): CLI + web app
├── src/core/               framework-agnostic engine (pinyin, layouts, vector PDF)
├── src/cli.ts              Node CLI (single / --file / --batch)
├── web/                    zero-install browser app (paste → preview → download)
├── data/characters.json    curated pinyin + English
└── fonts/                  bundled char + pinyin fonts

chinese_tools/            # the remaining Python tools (one package)
├── kahoot/                 build Kahoot question spreadsheets (CSV/XLSX)
├── game/matching_game.py   pygame character-matching game
├── data/                   curated pinyin/English readings + tone decoder
├── settings.py             shared settings (game)
└── paths.py                filesystem paths

worksheets/               # ready-to-print PDFs + their source character lists
tests/                    # pytest suite (Python side)
```

## Tools

### Card maker — `cardmaker/` (TypeScript)

Print-ready vector PDFs: 米字格 practice cards (`big` / `grid`), tracing/repeat
practice, vocab flashcards (word + pinyin + English), and stroke-order diagrams.
Run it as a CLI or the in-browser web app — see
[`cardmaker/README.md`](cardmaker/README.md).

```bash
cd cardmaker && npm install
npx tsx src/cli.ts --file ../worksheets/yr1_chars.txt   # batch/regenerate PDFs
npm run web:dev                                         # the web app, locally
```

See [`worksheets/README.md`](worksheets/README.md) for the ready-made Year 1–6
PDFs and how to regenerate them.

### Kahoot processor — `chinese_tools.kahoot.processor`

Builds Kahoot question spreadsheets in bulk, so you don't enter questions one by
one on the website.

### Matching game — `chinese_tools.game.matching_game`

A pygame memory-matching game over generated character images.

```bash
pip install -r requirements.txt   # Python tools (Kahoot + game)
```

## Tests

```bash
cd cardmaker && npm test   # card maker (TypeScript)
pytest -q                  # Python tools
```

## Credits

By [John Ni](mailto:chaussen@gmail.com). The matching game is based on
[Memory_Match](https://github.com/ncarmine/Memory_Match).
