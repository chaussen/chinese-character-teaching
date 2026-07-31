# 《中文》 Worksheet Generator

Internal **classroom drill sheet** generator for CFCS Saturday classes, keyed to
the Jinan University 《中文》 (修订版) series — 12 volumes, ~2110 生字.

You specify a lesson and a duration. It builds a sheet to fit, checks every
answer key, and hands back one self-contained print-ready HTML with the key on a
separate page.

```bash
python -m zhw.build --book 3 --lesson 3 --lesson 4 --minutes 45
```

---

## The architecture in one paragraph

Curriculum content is **data**, never code and never model output. You ingest a
lesson's 生字表, 词语, 句型 and 课文 once; enrichment (pinyin, radical,
decomposition, stroke count, stroke-order paths) is derived automatically from
open data and is always overridden by anything the textbook says. Question types
are **pluggable generator functions** that read from a *scope* — the closed
vocabulary window a student has actually been taught. A *recipe* pins a
worksheet's scope, sections and random seed, so the same recipe reprints
byte-identically forever, and a new seed produces a fresh variant of the same
worksheet. A build-time QA gate fails the build if any question would put an
untaught character in front of a student.

```
  生字表 / fed chars ──▶ ingest ──▶ corpus.json ──▶ enrich (pinyin/部首/笔顺)
                                          │
                              scope  ◀────┘   (lesson | book | cumulative)
                                │
              recipe ──▶ 31 question generators ──▶ QA gate ──▶ print HTML
                (seed)                              (leak check)   + answer key
```

---

## Install

```bash
pip install -r requirements.txt
./fetch_data.sh          # one-time, ~32MB: makemeahanzi stroke/radical data
```

`fetch_data.sh` pulls [makemeahanzi](https://github.com/skishore/makemeahanzi)
(CC BY 4.0). Everything still works without it — you just lose stroke counts,
stroke-order strips, radicals and component decomposition.

---

## Four ways to run it

**1 — A lesson, built to a duration**

```bash
python -m zhw.build --book 3 --lesson 3 --lesson 4 --minutes 45
python -m zhw.build --book 3 --lesson 3 --minutes 30 --density compact
```

**2 — A whole book, one worksheet per lesson**

```bash
python -m zhw.build --book 3 --all --minutes 45 --out out/book3
```

Types with no material in a lesson are dropped silently and reported, so a
thin early lesson and a rich later one both produce a valid sheet.

**3 — Characters fed straight in, no corpus at all**

```bash
python -m zhw.build --chars 店区近边邮银 \
  --words "商店 附近 旁边 银行" \
  --sentences "我家附近有一个商店。|银行在学校的旁边。" \
  --minutes 30
```

**4 — A pinned recipe (the one to use for anything you'll reprint)**

```bash
python -m zhw.build --recipe recipes/b3l3-standard.yaml
```

A recipe can either hand-pick `sections:` (byte-for-byte control) or give
`minutes: 45` instead — same duration planner as `--minutes` below, so the
recipe fills to a real class length from actually generated, measured
sections rather than a fixed list that might run short. See
`recipes/b9l3-review.yaml` for a `minutes:`-planned example; generated
sections are grouped back under `一、字 / 二、音 / ...` headings automatically
by question category.

Other flags: `--types trace,word_search,cloze` (override the preset),
`--density compact|spacious`, `--no-key`, `--seed N`, `--strict`,
`--vocabulary lesson|book|cumulative`, `--list-types`.

---

## Mixing in review characters from earlier books

A student practising book 9 hasn't necessarily retained everything from books
7 and 8 — and may not even have finished book 9 yet. `--vocabulary cumulative`
only widens the *allowed* window (distractors, padding, cloze fillers); it
never puts an older character in front of the student as something to
actually read or write. `--review-books` does that on purpose:

```bash
python -m zhw.build --data data/book9.json,data/book7.json,data/book8.json \
  --book 9 --lesson 3 --preset standard \
  --review-books 7,8 --review-ratio 0.35
```

`--data` takes one path or several **comma-separated** paths — each book lives
in its own file (`data/book7.json`, `book8.json`, `book9.json`, …), and
`--review-books` needs their lessons actually loaded to draw from. `Scope`
picks a fixed, reproducible subset of characters from those books (same seed
=> same review mix, not re-rolled per section) and folds it straight into
`practice_chars()` — the same pool `trace`, `stroke_count`, `pinyin_write`,
`lookalike`, `make_words`, `gloss_match`, `word_search` and every other
character-based type samples from. The build report's `"review"` key lists
exactly which characters were pulled in and from which books; the printed
sheet's teacher note shows the count alongside the usual 生字/词语 totals.

Flags: `--review-books 7,8` (which finished books to draw from) ·
`--review-ratio 0.35` (fraction of the character pool that should be review
material — `round`ed against the lesson's own character count) ·
`--review-count N` (a fixed number instead of a ratio) · `--review-tier
write|read` (default `write`). The equivalent recipe field:

```yaml
scope:
  book: 9
  lessons: [3]
  vocabulary: cumulative
  review:
    books: [7, 8]
    ratio: 0.35
    tier: write
```

See `recipes/b9l3-review.yaml` for a full pinned example. Review characters
count as already-taught for the closed-vocabulary gate regardless of the
`vocabulary` setting — a `lesson`-scoped sheet won't flag them as leaks.

---

## Ingesting a lesson

The paste format is designed to be typed straight off the 生字表 page:

```
book: 3
lesson: 4
title: 买东西
write: 买 卖 东 西 钱 元
read: 多 少 块
words: 东西 dōngxi thing / 多少 duōshao how many / 一块 yí kuài one dollar
patterns: ……多少钱？
sentences: 这个多少钱？| 我买两个。
antonyms: 买-卖 | 多-少
measures: 块-钱
passage: 星期六，我和妈妈去买东西。……
---
book: 3
lesson: 5
...
```

Separate lessons with `---`. TSV (`char⇥pinyin⇥gloss⇥tier⇥words`) and raw JSON
are also accepted. `tier` is `write` (四会字) or `read` (二会字) — the generator
only sends `write` characters to handwriting tasks.

---

## Correctness classification (read this first)

Content correctness beats variety. Every type is classified by **how its answer
key is justified**, and the two weakest tiers behave accordingly.

| tier | what the key rests on | default |
|---|---|---|
| `verified` | machine-provable from the lesson data | on |
| `authored` | teacher-written items in the lesson file | on |
| `open` | no single key; marked against stated criteria, printed as such | on |
| `derived` | auto-enrichment that may not match the textbook | **off** |

`python -m zhw.build --audit` prints the full list with the risk on each type.

### What was cut, and why

**Moved to `derived` (disabled unless you pass `--allow derived`)**

* `radical_id`, `radical_sort` — makemeahanzi gives the *Kangxi* radical.
  Dictionaries and 《中文》 disagree on the 部首 of plenty of characters (和, 相,
  期…), so the key is arguable. Put `radical` in your lesson data and these
  become dependable.
* `stroke_order` — the marked answer would be makemeahanzi's stroke order, which
  is not guaranteed to match the 笔顺规范 taught in class.
* `component_build` — IDS decomposition produces non-characters (亅, 卜, ？) and
  splits that are not how the character is taught.
* `trace` keeps its 田字格 rows but its stroke-order strip is now **off by
  default** (`params: {stroke_order: true}` to opt in) — same data, same doubt.

**Rewritten to run only on teacher-authored items**

* `cloze` — auto-cloze was unsound. Code cannot tell whether a second bank word
  also fits the gap ("我去＿＿。" takes 学校 *or* 公园). It now reads a `cloze`
  block from the lesson data.
* `true_false` — the old version made a "false" statement by swapping two chunks,
  which frequently produced another perfectly correct sentence (我和哥哥 →
  哥哥和我). Now reads a `truefalse` block.
* `passage_read` — same defect: distorting a sentence does not reliably make it
  false. Now pairs the 课文 with authored `truefalse` and `comprehension` items.

**Deleted**

* `odd_one_out` — semantic grouping cannot be verified without declared
  categories. `group_sort` replaces it and refuses to run without a `groups`
  block, rejecting any word listed under two categories.

**Re-marked `open` rather than pretending to a single key**

* `scramble` (连词成句) — chunks can usually be validly reordered, so the answer
  key now prints the textbook sentence as the *model* answer and states plainly:
  accept any fluent, correctly punctuated sentence using every chunk.

**Guards added to types that stayed**

* `pinyin_write`, `tone_mark`, `pinyin_match` now skip 多音字 entirely, and skip
  any character whose reading was auto-filled rather than given by the textbook.
  Asking for "the" pinyin of 长 or 的 in isolation has no single answer.
* `pinyin_read` uses whole words only, and only where no other in-scope word
  shares that reading.
* `gloss_match`, `word_meaning_mcq` refuse auto-filled glosses — dictionary
  English ("ice", "to be") is not the meaning taught in class.
* `stroke_count` prefers teacher-supplied counts. With none available the
  question is stamped `provenance: derived` and dropped, which is why you will
  see it skipped on lessons where you have not entered counts yet.
* `char_maze` returns nothing rather than risk a second valid path when there are
  too few non-target characters to pad with.

### The two extra data blocks this needs

```
cloze: 我去＿＿上学。=学校 | 他是我的＿＿。=同学
truefalse: 公园里有大树。=T | 我家有三个人。=F
comprehension: 我家有几个人？=五个人。 | 我们去哪里？=去公园。
```

Fifteen minutes per lesson buys you `cloze`, `true_false` and `passage_read` with
keys you can defend to a parent. Without them those three simply do not appear.

---

## Building to a duration

`--minutes N` is the main control. The planner does not guess: it generates each
candidate section for real, measures it, then accepts, trims or drops it.

```
target 45.0 -> 41 min work + 3 settling = 44 | 9 sections, 89 items, 4.53 pages
plan:
   minimal_pairs: +16 items, 6.3 min
   pinyin_partial: +16 items, 6.8 min
   pinyin_write: +12 items, 4.4 min
   lookalike: +10 items, 3.8 min
   pinyin_match: +8 items, 2.8 min
   tone_mark: +10 items, 3.1 min
   cloze: +9 items, 5.2 min
   scramble: +5 items, 5.4 min
   passage_read: +3 items (trimmed to fit), 3.7 min
```

The last 30% of the budget is **reserved for production work** (`--production-share`),
so fast recognition drills can never eat the whole lesson and leave nothing
written. Sections run warm-up → recognition → production, like the CRAN paper.

If the scope cannot fill the time, it says so and says what would fix it:

```
"shortfall": "9 min short of target — the scope ran out of material.
              Widen it (more --lesson flags), or author cloze / truefalse /
              comprehension items for these lessons."
```

Skipped sections report the real reason, not a shrug:

```
cloze: SKIPPED — bank-word-in-sentence: bank word '个' already sits in the
       sentence needing '东西'
```

### The timing numbers are estimates — calibrate them

Every duration in this tool comes from `data/timing.json` and nowhere else:
seconds per item per question type, plus per-section overhead and a settling
allowance. **They are my estimates, not measured.** Time one real class, edit the
numbers, and every future sheet is right. That file is the only thing to touch.

---

## Sheet conventions

This is a **classroom exercise sheet**, not an assessment, and the layout says so.

* **No marks anywhere.** No per-question tally, no total, no 得分 field. Students
  read a score column as "this is a test". `--marks` turns all of it on if you
  ever do want an actual assessment.
* **No time on the sheet.** The duration is teacher information; it lives in the
  build report and on the answer key, not in front of the student.
* **One blank affordance per answer, never two.** Brackets `（　　）` *or* a ruled
  line — never a rule inside brackets. `render.bracket()` and `render.blank()`
  are the only two, and mixing them is a test failure.
* Teacher metadata (item counts, 生字 totals, estimated minutes) sits on the
  answer-key page.

`tests/test_layout.py` enforces all of the above, plus a check for any CSS class
used in the HTML but not defined in the stylesheet — that one caught a bug where
a removed style left every 组词 bracket rendering at zero width.

---

## Two layout styles

`--style drill` (**default**) is the classroom paper: dense, plain, Chinese
question numbering 一、二、三, `1 × 24 = 24` mark tallies in the heading, hairline
rules instead of boxes, high item density. `--style workbook` is the same content
with scaffolding — 田字格 rows, boxed word banks, wider spacing — kept for the
occasional handwriting-focused sheet. Same CSS foundation, so they look like
siblings.

`--lang both|zh|en` controls the bilingual instruction line. `--density
compact|spacious` tightens or opens the vertical rhythm; compact typically saves
a page on a long sheet.

Every build reports an estimated page count, calibrated against real Chromium A4
renders (`tools/calibrate.py` re-fits it if you change the CSS), plus a warning
when a sheet barely spills:

```
"est_pages": 2.04,
"page_warning": "~2.04 pages: the last page is only 4% used.
                 Try --density compact, or drop one section."
```

---

## The two build-time gates

### 1. Answer uniqueness

*This is the fix for matching and grouping questions coming out wrong because of
the internal link rather than the content.*

Every question carries a machine-readable key alongside its HTML, and declares
how it can be marked:

| mode | meaning | checked |
|---|---|---|
| `bijection` | matched from a shared pool — 连线, single-use banks, sorting | one-to-one link enforced |
| `unique` | independent items, one right answer each | key completeness |
| `open` | many answers valid — 组词, 造句, 写话 | key printed as examples |
| `teacher` | needs human judgement | **rejected — never printed** |

Generic checks catch an empty answer, a repeated prompt, a distractor that is
also correct, and — for `bijection` — two items sharing an answer or one answer
nested inside another. Type-specific checks go further:

* **连线** pre-filters characters sharing a reading and glosses nested in
  each other, *then* verifies the link is one-to-one
* **选词填空** rejects a bank word that already sits in one of the sentences, a
  target occurring twice in its own sentence, or a word that would also fit
  another gap
* **形近字 / 同音字** rejects a distractor that itself forms a real in-scope word
* **字词搜索** re-rolls the padding until no target word can be found twice
* **判断对错** rejects a "wrong" sentence that is accidentally a real one
* **根据拼音写字** rejects a gap where a second in-scope character with the same
  reading also makes a real word
* **部首归类** rejects a character that could be argued into two buckets
* **量词 bank** verifies bank and key are a true one-to-one match, and that no
  two measure words are interchangeable between their nouns
* **排列句序** refuses to run on an unordered example list — it needs a real 课文

A failing question is re-rolled with a fresh sub-seed up to six times, then
dropped and reported:

```json
"rejected_for_ambiguity": {
  "pinyin_match": ["ambiguous-link: two items share an answer: ['mā']"]
}
```

`找不同类` was **retired**: semantic grouping cannot be verified without declared
categories. Its replacement, `group_sort`, only runs when the lesson data
supplies a real `groups` block — and rejects any word listed under two
categories. No question ships with "teacher-judged" as its key.

`tests/test_validate.py` feeds eight known-bad questions through the checker and
asserts each trap fires. Run it after touching a generator.

### 2. Closed vocabulary

Every question declares every Hanzi a student has to *read*. At build time each one is checked against the cumulative
set of characters taught up to that lesson. The build report tells you exactly
what leaked:

```json
"leaks": { "14. cloze": ["候", "第"] },
"advisories": { "6. component_build": ["亻", "卜", "门"] }
```

*Leaks* block a `--strict` build. *Advisories* are inherent to the type
(component fragments aren't taught characters) and are reported for review only.
This catches the single most common failure in hand-made worksheets: a filler
word, distractor or puzzle padding character the class hasn't met yet.

---

## Question types (35 registered, 31 enabled by default)

| 字形 form | 拼音 sound | 词义 meaning |
|---|---|---|
| `trace` 描红写字 | `pinyin_write` 看字写拼音 | `gloss_match` 汉英连线 |
| `stroke_count` 数笔画 | `pinyin_read` 看拼音写汉字 | `make_words` 组词 |
| `lookalike` 形近字选择 | `pinyin_partial` 根据拼音写字 | `word_meaning_mcq` 词语选择 |
| `minimal_pairs` 比一比再组词 | `tone_mark` 标声调 | `antonym` 反义词 |
| *(off: `radical_id`, `radical_sort`,* | `pinyin_match` 拼音连线 | `group_sort` 分类 |
| *`stroke_order`, `component_build`)* | `homophone` 同音字 · `dictation` 听写 | |

**Classroom drill types** (modelled on the CFCS/CRAN unit-test format):
`minimal_pairs` 照例子比一比，再组词语 (braced 形近字 pairs — only pairs sharing a
real component are accepted) · `pinyin_partial` 根据拼音写出中文字词 (pinyin above a
gap inside a partial word) · `use_the_word` 用划线的词造句 · `measure_bank`
选择正确的数量词 (one shared bank, each word used once) · `group_sort` 分类.

| 句子 sentence | 阅读 reading | 游戏 puzzle | 书写 production |
|---|---|---|---|
| `scramble` 连词成句 | `passage_read` 短文阅读 | `word_search` 字词搜索 | `word_build_boxes` 抄写词语 |
| `cloze` 选词填空 | `sentence_order` 排列句序 | `char_maze` 汉字迷宫 | `free_write` 看图写话 |
| `measure_word` 量词填空 | | `code_breaker` 密码句子 | |
| `pattern_write` 照样子写句子 | | `bingo_card` 汉字宾果 | |
| `true_false` 判断对错 | | | |

Sentence, cloze, reading and code-breaker types **only re-present textbook
sentences** — as scrambles, gapped items, ordering tasks or codes. Nothing here
writes new Chinese prose.

### Presets

Prefer `--minutes`. Fixed presets remain for specific jobs:
`classroom` (~20 min) · `classroom_lite` (one page) · `unit_test` (the CRAN shape:
pairs, pinyin gaps, 选词填空, 造句, 量词 bank, 短文阅读) · `starter`
(recognition-first, new class) · `revision` (no new writing) ·
`dictation` (teacher's 听写 list) · `bingo` (a card per seed) ·
`standard` / `full` (scaffolded, for the workbook style).

---

## Adding a question type

Twenty lines, one decorator, no other file touched:

```python
@register("my_type", "我的题型", "My question type", "form",
          default_count=6, minutes_each=0.4)
def my_type(ctx: Ctx) -> Question | None:
    chars = ctx.pick(ctx.write_chars(), ctx.count)
    if not chars:
        return None                      # no material -> silently skipped
    return Question(
        type_id="my_type", title_zh="…", title_en="…",
        instruction_zh="…", instruction_en="…",
        body_html="…", answer_html="…",
        student_hanzi="".join(c.char for c in chars),   # feeds the vocabulary gate
        solution=[(c.char, str(c.stroke_count)) for c in chars],  # feeds the key gate
        answer_mode="unique",
        marks=len(chars), marks_each=1, items_n=len(chars),
        est_minutes=0.4 * len(chars))
```

`ctx` gives you seeded sampling (`ctx.pick`, `ctx.shuffled`, `ctx.distractors`),
the target lesson's material and the full allowed window. Render helpers:
`tianzige`, `tzg_row`, `stroke_sequence`, `stroke_order_svg`, `wordbank`,
`blank`, `writing_lines`.

---

## Print contract

Fixed on purpose — consistency across every sheet is the point.

* A4 portrait, 12mm/14mm margins, greyscale-safe (no colour carries meaning)
* every question is `break-inside: avoid`
* the answer key always starts on a fresh page
* 楷体 font stack for all model characters, sans for instructions
* screen toolbar (print / toggle answer key / toggle pinyin / density) is
  `display:none` in print
* **print at 100% scale with browser headers and footers switched off**
* every footer carries `recipe-id · seed · date` so any printed sheet can be
  regenerated exactly

---

## Reproducibility

Same recipe + same seed → byte-identical HTML. Change the seed → a new variant of
the same worksheet (useful for A/B papers, resits, or a bingo card per student).
Each question type gets its own derived RNG stream, so adding a section never
reshuffles the sections above it.

---

## Layout

```
zhw/
  model.py        records, Corpus, Scope, closed-vocabulary logic
  ingest.py       block / TSV / JSON ingest, ad-hoc character feed
  enrich.py       pypinyin + makemeahanzi; 形近字 and 同音字 detection
  render.py       print CSS, 田字格, stroke-order SVG, worksheet assembly
  validate.py     answer-uniqueness checks + per-type ambiguity traps
  build.py        CLI, presets, recipes, both gates, batch, page estimate
  qbank/          form · sound · meaning · sentence · reading · puzzle · drill
tests/            ambiguity-trap self-test
tools/            page-estimator calibration
data/             corpus JSON (sample included — replace with the real 生字表)
recipes/          pinned worksheet definitions
vendor/           makemeahanzi (fetch_data.sh)
```

`data/zhongwen.sample.json` is **illustrative demo data**, not the official
生字表. Replace it before classroom use.

---

## Worth adding next

1. **Calibrate `data/timing.json` against one real 45-minute class.** Everything
   downstream — planning, trimming, the shortfall warning — is only as good as
   those numbers, and right now they are guesses.
2. **Audio.** Pipe the `dictation` answer key through the local CosyVoice2 stack
   and drop a QR code in the header — the 听写 sheet becomes self-serve, and the
   survey's top request (spoken Chinese) gets an at-home channel that doesn't
   need a Mandarin-speaking parent.
3. **Stream S / Stream L variants.** Same recipe, two presets — Stream S drops
   `stroke_order`/`pattern_write`, Stream L adds `passage_read`/`free_write`.
   One command, two sheets.
4. **A per-student difficulty seed** so a class of 20 gets 20 non-identical
   sheets from one recipe (kills copying, same marking key structure).
5. **Coverage report across a book** — which 生字 have appeared in how many
   worksheet questions, so nothing gets under-practised.
6. **A tiny local web form** over `build.py` once the recipe library stabilises.
   Not before: the CLI plus recipe files is faster to batch and easier to diff.
