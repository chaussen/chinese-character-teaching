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

The generator is `../src/locals/worksheet_maker.py` (needs `Pillow` and
`xpinyin`: `pip install Pillow xpinyin`).

```bash
# rebuild every *_chars.txt in this folder
python ../src/locals/worksheet_maker.py --batch . --outdir .

# one list
python ../src/locals/worksheet_maker.py --file yr1_chars.txt

# ad-hoc characters
python ../src/locals/worksheet_maker.py --chars "花园门前"

# compact multi-cell sheet instead of big cards
python ../src/locals/worksheet_maker.py --file yr1_chars.txt --layout grid --cols 8
```

## 多音字 (multiple readings)

Pinyin defaults to the most common reading. To force a reading, annotate the
character in the `.txt` list (tone marks or tone numbers both work):

```
重(zhòng) 重(chóng) 行(háng) 数(shǔ)
重(zhong4)
```

Run `python ../src/locals/worksheet_maker.py --help` for all options
(`--dpi`, `--margin-mm`, `--char-font` for a 楷体/Kaiti font, `--png`, etc.).
