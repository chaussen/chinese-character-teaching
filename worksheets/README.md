# Character practice cards

Print-ready A4 PDFs of Chinese character handwriting practice. Each character
sits in a 米字格 (solid border, dashed cross + diagonals) with its pinyin on top
in a 四线三格 four-line guide.

## Files

| List | PDF | Notes |
|------|-----|-------|
| `yr1_chars.txt` … `yr6_chars.txt` | `yrN_character_cards.pdf` | Year 1–6 character lists |

Each PDF uses the **big** layout: two large characters per A4 portrait page,
each rotated 90° ("lying down"). Cut along the dashed middle line and turn each
half upright — the character fills almost the whole card.

## Regenerate

The generator is `chinese_tools/cards/worksheet_maker.py` (needs `Pillow` and
`xpinyin`: `pip install Pillow xpinyin`). Run from the repository root:

```bash
# rebuild every *_chars.txt in this folder
python -m chinese_tools.cards.worksheet_maker --batch worksheets --outdir worksheets

# one list
python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt

# ad-hoc characters
python -m chinese_tools.cards.worksheet_maker --chars "花园门前"

# compact multi-cell sheet instead of big cards
python -m chinese_tools.cards.worksheet_maker --file worksheets/yr1_chars.txt --layout grid --cols 8
```

## 多音字 (multiple readings)

Pinyin defaults to the most common reading. To force a reading, annotate the
character in the `.txt` list (tone marks or tone numbers both work):

```
重(zhòng) 重(chóng) 行(háng) 数(shǔ)
重(zhong4)
```

Run `python -m chinese_tools.cards.worksheet_maker --help` for all options
(`--dpi`, `--margin-mm`, `--char-font` for a 楷体/Kaiti font, `--png`, etc.).
