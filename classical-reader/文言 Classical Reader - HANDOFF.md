# 文言 · Classical Chinese Close Reading — Engineering Handoff

A learning module for **classic Chinese literature (文言文)** aimed at **near-native / advanced** learners.
Design language is shared with the suite's entry point (top bar, Casey Chinese School branding, coral/paper palette) but the product is otherwise **standalone** — treat content, schema, and learning system as its own thing.

> **Shipped app:** `index.html` — a self-contained vanilla HTML/CSS/JS port of the prototype, deployed to **`/classical-literature/`** by `.github/workflows/deploy-pages.yml` and linked from the landing hub. No build step, no framework, no external deps; the content (`DATA`/`LOCKED`) is inline. Open it directly in a browser.
>
> The port applies the **v2 wireframe corrections**: on-screen colour = **grammar role** (`cats`, §1b), reading hazards (`duo`/`rare`/`loan`/`phrase`) are **note chips, not glyph colours** (§1c), and artifact pinyin reads **horizontally & upright** (the `.artifact rt` rule). A `validate()` guard logs any line where Han-glyph count ≠ pinyin-syllable count, or any `cats` index out of range.
>
> **Prototype file:** `Classical Reader.dc.html` (the original Design Component, kept as the design source) + `Reader v2 Wireframe.dc.html`.
> Everything below describes how to take the inline `DATA` and grow it into a content pipeline that can hold **bulky corpora (e.g. 二十四史)** without hand-authoring every character.

---

## 1. What the product does

Three reading modes over one vertical-text artifact (authentic right-to-left columns, author seal, colophon):

| Mode | 中文 | What the learner gets |
|---|---|---|
| **Read** 通读 | 通读 | Bare columns + tap-to-hear (TTS). Side panel = 题解 / 主旨 / 读法 only. |
| **Study** 精读 | 精读 | Tap a column → per-character **pinyin** (upright, horizontal — see §1a), a **simple modern-Chinese** paraphrase, an **idiomatic English** reading, a **字词** list of words that shift meaning, and a **成语** card when the line births an idiom. |
| **Recite** 背诵 | 背诵 | Text is masked; the panel cues you with **meaning**; you recall the 文言 and tap each covered column to check. Progress tracked. |

**Pinyin** is global, toggled by the 拼音 On/Off control in the reader sub-bar. Default On. Advanced learners can switch it off to read raw, then flip it on to check.

### 1a. Pinyin presentation — direction & title romanization
- **The text runs vertically (vertical-rl), but pinyin must read horizontally and upright** — one syllable laid out left→right beside its character. Rotated-sideways or letter-stacked pinyin (the default when `text-orientation:upright` cascades into the ruby annotation) is rejected. Implementation: ruby base inherits the vertical/upright column; the `<rt>` is forced back to `writing-mode: horizontal-tb; text-orientation: mixed`. (See `Reader v2 Wireframe.dc.html`.)
- **Title and author are romanized and translated** wherever they appear (artifact colophon, headers): 陋室铭 · **Lòushì Míng** · “Inscription for a Humble Room”; 刘禹锡 · **Liú Yǔxī** · 772–842. The schema carries `titlePy` and `authorPy` for this.

### 1b. On-screen color = GRAMMAR ROLE (not pinyin difficulty)
For a near-native reader the useful signal is **what each word is doing**, and 虚词 (function words) saturate 文言文. Tagged characters get a thin underline in their category color + a legend; the study panel repeats the label in words. Five categories (`cat` field, per-character):

| `cat` | tag | 中文 | English | examples | color |
|---|---|---|---|---|---|
| `aux`   | 助 | 助词·虚词 | particle / function word | 之 而 则 者 也 矣 焉 乎 | `#3F6B8C` slate |
| `pron`  | 代 | 代词 | pronoun | 予 吾 斯 何 | `#6C5AA6` violet |
| `flex`  | 活 | 活用 | word-class shift | 名→动 (名 灵 上 蔓) · 使动 (乱 劳) | `#B0772A` amber |
| `name`  | 名 | 人名 | person | 诸葛 子云 孔子 陶渊明 | `#4E7D4E` green |
| `place` | 地 | 地名·朝代 | place / dynasty | 南阳 西蜀 李唐 | `#2C7A70` teal |

Extend the set as corpora demand (e.g. 官名 office titles, 数 numerals) — keep it small and legible.

### 1c. The three pinyin hazards — DATA-ACCURACY flags, NOT on-screen color
These are **where auto-pinyin gets it wrong**, so they are review flags in the build step and a per-line 字词 note — never a color the learner must decode. Encoded as reading exceptions (§4) + an optional `reading` tag on the relevant `notes` entry:

1. **多音字 (context reading)** — char whose reading is fixed by context: 调 **tiáo** (not diào) in 调素琴; 鲜 **xiǎn** (not xiān); 蔓 **màn**; 葛 **gě** (surname).
2. **生僻 (rare graph)** — uncommon char whose mainstream reading must be pinned: 馨 xīn, 牍 dú, 濯 zhuó, 亵 xiè, 噫 yī.
3. **通假 / 借字 (loan character)** — a char standing in for another (**not** a 多音字); the reading follows the borrowed word: 蕃 read **fán** (= 繁) in 可爱者甚蕃. (The 狐假虎威 fable spotlights 假 = **jiǎ**, the canonical 借字 case.)

Plus a segmentation concern — **连读 / atomic groups** (鸿儒, 白丁, 案牍, 牡丹, 亵玩): individually sensible characters that should be perceived as one unit. Handled by the segmenter and a 字词 note, not by color.

> These four are exactly where naive converters fail; the override table (§4) and human review exist to fix them. They do **not** drive the UI palette — grammar role (§1b) does.

---

## 2. Where the data lives

**Today (prototype):** all content is inline in `Classical Reader.dc.html` → the `DATA` object inside `class Component`. Two fully-built texts (`louver` = 陋室铭, `lotus` = 爱莲说) plus a `LOCKED` array of idiom-rich "coming soon" cards.

**For scale:** lift `DATA` out into a content directory and lazy-load. Proposed layout:

```
/content
  manifest.json            # library index: id, title, author, dynasty, genre, count, idiom, status, file
  /texts
    louver.json            # one file per short text  (陋室铭)
    lotus.json             # (爱莲说)
    ...
  /corpora                 # bulky multi-chapter works
    /shiji                 # 史记
      manifest.json        # chapter index for this work
      063-laozi-hanfei.json
      ...
  /overrides
    readings.json          # global + per-text reading exceptions (see §4)
```

The component should fetch `manifest.json` for the library screen, then fetch a single text/chapter JSON on open. Nothing else needs to be in memory.

---

## 3. Content schema (the contract)

A **text** = metadata + ordered **lines** (a "line" = one clause/breath unit, the tap target). Keep it flat and serializable.

```jsonc
{
  "id": "louver",
  "title": "陋室铭",
  "titleEn": "Inscription for a Humble Room",
  "dynasty": "唐",
  "author": "刘禹锡",
  "dates": "772–842",
  "genre": "铭",
  "count": "81",
  "seal": "刘",                // 1 char for the seal chip
  "colophon": "唐 · 刘禹锡",
  "intro":  { "cn": "...", "en": "..." },   // 题解
  "theme":  { "cn": "...", "en": "..." },   // 主旨
  "craft":  { "cn": "...", "en": "..." },   // 读法
  "lines": [
    {
      "zh": "可以调素琴，阅金经。",
      "py": "kě yǐ tiáo sù qín yuè jīn jīng",   // space-separated, ONE syllable per Han char, punctuation skipped
      "cats": {},                               // ON-SCREEN color = grammar role: key = Han-char index, value = aux|pron|flex|name|place (§1b). none in this line
      "today": "可以弹奏不加装饰的古琴，阅读佛经。",  // simple modern Chinese — keep it plain
      "en": "Here one may tune a plain zither, or read the gilded sutras.", // idiomatic English — must read naturally
      "idiom": { "zh": "出淤泥而不染", "py": "chū yū ní ér bù rǎn", "en": "..." }, // optional, only when the line spawns a 成语
      "notes": [                                 // 字词 — the words that shift
        // `reading` = data-accuracy flag (§1c): duo|rare|loan — shown in the note, never as on-screen color
        { "w": "调", "py": "tiáo", "reading": "duo", "cn": "弹奏。此处读 tiáo，不读 diào（多音字）", "en": "to play / tune — read tiáo here, not diào" }
      ]
    }
  ]
}
```

### Alignment rule (important)
`py` is aligned to **Han characters only**. The renderer (`tokens()` in the component) walks `zh`, and for each character matching `/[\u4e00-\u9fff]/` it consumes the next syllable from `py`; punctuation consumes nothing. So **`py` must have exactly one syllable per Han character** — no syllables for punctuation. A validator should assert `hanCount(zh) === py.split(/\s+/).length` for every line, or the ruby silently misaligns.

`cats` keys are indices into that same Han-only sequence (grammar coloring, §1b). The pipeline's reading-accuracy flags (§1c) live on `notes[].reading` + the override table (§4), never in `cats`.

### Editorial bar for the two translations
- **Modern Chinese (`today`)** — simple and clear. The reader already knows Chinese; this disambiguates the 文言, it is not a literary rewrite.
- **English (`en`)** — **idiomatic and genuinely helpful, even when that means being more verbose.** This is the one place not to be terse. Natural English a fluent reader would actually write — and where a bare rendering would leave an English reader puzzled, spend the extra words: unpack the **cultural implication** (why a lotus rising clean from mud reads as moral integrity, not just botany), the **historical context** (who 诸葛 / 子云 were and why naming them flatters the room), allusions, wordplay, register, and anything that simply has no English equivalent. The 字词 `notes` carry the literal gloss; `en` carries the *understanding*. Better a sentence too long than a reader left in the dark.

---

## 4. Pinyin pipeline (auto-generate → review exceptions)

You cannot hand-key pinyin for 二十四史. The model is **auto-generate, then override**:

1. **Auto pass.** Run each line's `zh` through a phrase-aware converter — recommend **`pypinyin`** (Python) with `heteronym`-aware, jieba-segmented mode, or `g2pW` (neural 多音字 disambiguation, materially better on classical text). Emit the aligned `py` string.
2. **Exception override.** Apply `/content/overrides/readings.json` on top of the auto output. Two levels:

```jsonc
{
  "global": {                 // word/char → forced reading, applies everywhere
    "蕃": "fán",              // loan for 繁 in this register
    "予": "yú",               // as 1st-person pronoun
    "鲜有": "xiǎn yǒu"        // multi-char key wins over single-char
  },
  "byText": {                 // pin a reading at an exact position (textId → "lineIndex.hanIndex")
    "lotus": { "5.14": "xiè" }
  }
}
```
Resolution order: `byText` (most specific) → `global` multi-char → `global` single-char → auto. Keep the override file **small and reviewed** — it is the human-curated layer; the bulk stays automatic.

3. **Mark inference + review.** Auto-tag candidates, then a human confirms:
   - `duo`: char has >1 common reading AND converter/override changed it from the dictionary default.
   - `loan`: present in a curated 通假字 list (ships with the project) — never auto-guess loans.
   - `rare`: char frequency below a threshold (e.g. outside the top ~3500).
   - `phrase`: spans from the segmenter that are multi-char proper nouns / fixed binomes.
   A line with no marks is fine and common.

4. **成语 + 字词 extraction.** Run `zh` against a 成语 dictionary to populate `idiom`; `notes` stay human-authored (they carry the teaching), but a 文言 function-word list (之/而/则/焉/矣/者…) can pre-seed candidates.

> Net: a new text is *machine-drafted in seconds, then an editor only reviews the flagged minority* — the `marks`, the override hits, the two translations, and the notes.

---

## 5. Scaling to bulky corpora (二十四史 等)

The schema already chunks at the **line** level; the only additions for huge works are **chunking, lazy-load, and an index**:

- **Chunk by chapter (卷/篇/回).** One JSON per chapter under `/content/corpora/<work>/`, plus a per-work `manifest.json` (chapter id, title, char count, `status`). Never load a whole 史 at once.
- **Lazy load + cache.** Fetch a chapter on open; cache parsed chapters (in-memory LRU + optionally IndexedDB) so revisits are instant. The component holds only the active chapter.
- **Library is index-driven.** The home screen reads only the top-level `manifest.json`; cards (and the locked/coming-soon state) are data, not code. Add a text = add a file + a manifest row.
- **Streaming-friendly.** Because lines are independent and ordered, a chapter can render incrementally as it parses — good for long 列传.
- **Search later.** A precomputed inverted index over `zh` (and 成语) per work enables cross-corpus lookup without loading bodies.
- **Build step.** A `build/` script: `raw 文言 text → segment into lines → auto-pinyin → apply overrides → infer marks → extract 成语 → validate alignment → write JSON`. Idempotent; re-runnable when the override table improves.

### Validation gate (run in CI before publishing any text)
- `hanCount(zh) === syllableCount(py)` for every line.
- every `marks` key `< hanCount(zh)`.
- `loan` chars exist in the curated 通假 list.
- `idiom.zh` is a substring of some line's `zh`.
- `today` and `en` non-empty; `en` passes a "no raw gloss" lint (heuristic).

---

## 6. Content selection guidance

Bias the library toward **materials rich in 成语 and common idioms** (per product owner):
- **寓言** (each yields one idiom, ~40–70 字): 守株待兔, 刻舟求剑, 自相矛盾, 狐假虎威 (借「假」), 画蛇添足, 滥竽充数, 塞翁失马, 愚公移山 — *already stubbed in `LOCKED`.*
- **史传** (二十四史 列传/本纪): dense with 典故 and 成语 (四面楚歌, 破釜沉舟, 完璧归赵…). Chunk by 卷.
- **诸子 / 名篇**: 《论语》《孟子》selections, 唐宋八大家 短文.

Each yields high-value 成语 cards and keeps clause length manageable for the tap-to-study unit.

---

## 7. Component internals (where to wire the loader)

In `Classical Reader.dc.html` → `class Component`:
- `DATA` / `LOCKED` → replace with `manifest`-driven state + an async `loadText(id)` that fetches `/content/texts/<id>.json` (or a chapter path) and sets it as the current text.
- `tokens(line)` — the alignment walker. **Don't change the contract** (one syllable per Han char) without updating the validator.
- `buildStudyChars` / `buildArtifactChars` — ruby builders (horizontal study clause vs. vertical artifact). Reading marks → colors via `markColor()` (`duo`=#B26B00, `rare`=#2C6E63, `loan`=#B23A2B, `phrase`=#8A7F6B).
- `renderVals()` — view model; everything the template binds to is returned here.
- Read-aloud uses the browser Web Speech API (`zh-CN`); quality is device-dependent. For consistent audio, swap `speak()` for pre-generated TTS clips referenced per line (e.g. `line.audio`).

Modes, masking, progress, and the pinyin toggle are all in component state (`screen, textId, mode, sel, revealed, pyOn`) — no external deps.
