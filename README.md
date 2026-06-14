# Chinese Character Teaching Tools

A small collection of Python tools for teaching Chinese characters: A4
handwriting practice cards, flashcards, a Kahoot quiz-sheet generator, and a
matching game.

## Repository layout

```
chinese_tools/            # all the code (one package)
├── cards/
│   ├── worksheet_maker.py   # A4 practice cards (米字格 + pinyin) -> PDF   ← main tool
│   └── flashcard_maker.py   # legacy per-character JPG flashcards
├── kahoot/
│   ├── processor.py         # build Kahoot question spreadsheets (CSV/XLSX)
│   ├── columns.py           # Kahoot column headers
│   └── kahoot.txt           # sample question source
├── game/
│   └── matching_game.py     # pygame character-matching game
├── ui/
│   └── app.py               # Tkinter front-end tying the tools together
├── data/
│   ├── pinyin_data.py       # curated pinyin/English readings + tone decoder
│   ├── character_dict.py    # per-lesson character dictionaries
│   ├── common_characters.txt
│   └── curriculum_y34.txt
├── fonts/GB2312.ttf         # bundled character font
├── settings.py              # shared settings (flashcards + game)
└── paths.py                 # filesystem paths (font, data, output dirs)

worksheets/               # ready-to-print PDFs + their source character lists
tests/                    # pytest suite
generated/                # scratch output from the legacy tools (git-ignored)
```

## Setup

```bash
pip install Pillow xpinyin          # practice cards (the main tool)
pip install pinyin xlsxwriter       # + flashcards / Kahoot processor
pip install pygame                  # + matching game
```

Run tools as modules from the repository root, e.g.:

```bash
python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt
```

## Tools

### Practice cards — `chinese_tools.cards.worksheet_maker`

Generates print-ready A4 PDFs. Each character sits in a 米字格 (solid border,
dashed cross + diagonals) with its pinyin on top in a 四线三格 guide. The default
`big` layout puts two large characters per page, rotated 90° so you cut the page
in half. See [`worksheets/README.md`](worksheets/README.md) for full usage,
batch regeneration, and 多音字 overrides.

### Kahoot processor — `chinese_tools.kahoot.processor`

Builds Kahoot question spreadsheets in bulk, so you don't enter questions one by
one on the website.

### Matching game — `chinese_tools.game.matching_game`

A pygame memory-matching game over generated character images.

### Tkinter UI — `chinese_tools.ui.app`

A desktop front-end that wires the flashcard maker and Kahoot processor together.

## Tests

```bash
pytest -q
```

## Credits

By [John Ni](mailto:chaussen@gmail.com). The matching game is based on
[Memory_Match](https://github.com/ncarmine/Memory_Match).
