# Chinese Character Teaching Tools

Tools and web apps for teaching Chinese characters: a browser learning app, a
classical-text reader, print-ready handwriting practice cards (米字格 + pinyin),
vocab flashcards, stroke-order diagrams, and a Kahoot quiz-sheet generator.

## Public site (GitHub Pages)

A static site is assembled and published by GitHub Actions
(`.github/workflows/deploy-pages.yml`). Pages source must be **"GitHub Actions"**
(the legacy Jekyll "deploy from a branch" path is off).

| URL path                | Content                          | Source |
|--------------------------|----------------------------------|--------|
| `/`                      | Landing / hub                    | `landing/` |
| `/character/`            | Character Studio learning app    | `studio.html` + `learn/` + `audio/` |
| `/classical-literature/` | Classical Reader                 | `classical-reader/index.html` |
| `/history/`              | 史案 History KG Reader            | `history-reader/` |
| `/tools/cardmaker/`      | Card Maker web app (hidden, not linked from landing) | built from `cardmaker/` |
| `/tools/kahoot/`         | Kahoot tool info page (hidden, not linked from landing) | `chinese_tools/kahoot/web/index.html` |

To work on the Studio locally, serve the repo root and open `studio.html`
(it loads its engine and data from `learn/` and clips from `audio/`).

## Repository layout

```
landing/                  # public landing / hub page (served at /)
studio.html               # Character Studio shell (served at /character/)
learn/                    # Character Studio engine + data (vanilla JS)
audio/                    # edge-tts recordings (char / word / sentence)
classical-reader/         # Classical Reader app (index.html) + design source (served at /classical-literature/)
history-reader/           # 史案 history knowledge-graph reader (served at /history/)
tools/                    # content build pipeline + audio generator

cardmaker/                # ← the card maker (TypeScript): CLI + web app
├── src/core/               framework-agnostic engine (pinyin, layouts, vector PDF)
├── src/cli.ts              Node CLI (single / --file / --batch)
├── web/                    zero-install browser app (paste → preview → download)
├── data/characters.json    curated pinyin + English
└── fonts/                  bundled char + pinyin fonts

chinese_tools/            # the remaining Python tool (one package)
├── kahoot/                 build Kahoot bulk-import .xlsx quizzes from JSON lessons
│   └── lessons/              lesson vocabulary lists (JSON; see schema in README below)
└── data/                   numbered-pinyin tone decoder (glossary lives in cardmaker/data/)

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

### Kahoot quiz generator — `chinese_tools.kahoot`

Builds Kahoot bulk-import quiz spreadsheets from a JSON lesson vocabulary list, so
you don't enter questions one by one on the website. Each item's pinyin + English
meaning comes from the curated glossary the card maker also uses
(`cardmaker/data/characters.json`) — anything missing from it still gets a
computed pinyin reading (via `pypinyin`) but no English meaning, with a warning
so the gap gets noticed. Generation is deterministic (seeded), the correct
answer's column is actually randomized per question (the old script always put
it in column 1), and output goes straight to `.xlsx` — Kahoot's importer
rejects a plain `.csv`.

```bash
pip install -r requirements.txt   # Python tools (Kahoot)

# one lesson -> one quiz
python -m chinese_tools.kahoot generate \
  chinese_tools/kahoot/lessons/lesson10_huayuan.json -o out/lesson10.xlsx

# pool several lessons into one combined/shuffled quiz
python -m chinese_tools.kahoot mix lessons/*.json -o out/mixed.xlsx --count 20
```

A lesson file is JSON: `title`, `mode` (`hanzi_to_meaning` / `hanzi_to_pinyin` /
`pinyin_to_meaning`), a `question_template` containing `{prompt}`, the `items`
list, and optional `choices` (2-4, default 4), `time_limit` (one of Kahoot's
allowed values, default 20), and `seed`. See
`chinese_tools/kahoot/lessons/lesson10_huayuan.json` for a worked example.

## Tests

```bash
cd cardmaker && npm test   # card maker (TypeScript)
pytest -q                  # Python tools
```

## Credits

By [John Ni](mailto:chaussen@gmail.com).
