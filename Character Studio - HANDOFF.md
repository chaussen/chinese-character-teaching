# Character Studio — Handoff & Build Tracker

Engineering + content handoff for the classroom character app.
**Main file:** `Character Studio.html` · **Code/data:** `learn/`. Updated 2026-06-16.

This document is written for **Claude Code** to take the app forward (real audio,
content authoring, more books). Read it fully before changing anything.

---

## 1. What the app is

Lock (class code **2580**) → **Home** → Units/Lessons → Deck → **Learn** / **Exercises**.
Two clearly separated purposes:

- **Learn a character** — mirrors the school website's "Learn a Character" page, in-app:
  coloured stroke-order animation, pinyin, meaning, **radical + its meaning + a memory
  note**, **audio** (char / word / sentence), **词语 word**, **句子 sentence**, **小故事
  origin story**, plus finger-**trace**.
- **Exercises** — a skill-tagged **Exercise Hub** (听 Listen · 读 Read · 写 Write). NOT
  flashcards (removed). Every exercise trains one microskill.

Everything on Home is grouped **Series → Book → Lesson → Character**.

---

## 2. Files

| File | Role |
|---|---|
| `Character Studio.html` | shell: all views + script tags. CSS cache-bust `studio.css?v=YYYYMMDD`. |
| `learn/studio.css` | all styles. |
| `learn/app.js` | engine: lock, routing, Home(series)/Units/Deck/**Learn**, the stroke **writer**, finger-trace, `CHAR_INDEX`, Library/series resolver, **audio (file → TTS)**. Exposes `window.STUDIO`. |
| `learn/exercises.js` | Exercise **Hub** + session controller + MCQ/match/order/listen/word/fill. `window.Exercises`. |
| `learn/exercises-draw.js` | writing exercises: **描红 trace** (coverage check) + **结构 structure** builder. `window.ExercisesDraw`. |
| `learn/app-data.js` | the **school's four-book series** (B1–B4), the taught Write characters, with stroke data. |
| `learn/general-data.js` | **General Characters** themed library, with stroke data. |
| `learn/library-data.js` | **added book series** (中文 pilot). Lists Hanzi only; resolved via `CHAR_INDEX`. |
| `learn/radicals.js` | **radical dictionary** → radical name + English meaning + memory note for every character (no per-char authoring). |
| `learn/content-extra.js` | **per-character enrichment** keyed by Hanzi: `origin`, `word`, `sentence`, `struct`. Optional — missing = hidden. |
| `learn/audio-index.js` | **audio manifest** (`window.AUDIO_INDEX`). Lists which recordings exist; empty = use TTS everywhere. |

**Data load order** (in the HTML, before `app.js`): app-data → general-data → radicals →
content-extra → audio-index → library-data → app.js → exercises-draw → exercises.

---

## 3. Core model & how it all connects

```
SERIES  (a course/publisher)             Home renders one section per series
  └─ BOOK  (a volume, e.g. 中文第一册)     unified .bookcard; id is the progress key
       └─ LESSON / UNIT / THEME           lists Hanzi
            └─ CHARACTER (by Hanzi)
                 ├─ stroke data   ← CHAR_INDEX  (app-data + general-data)   SHARED
                 ├─ radical info  ← radicals.js  (by radical glyph)         SHARED
                 ├─ enrichment    ← content-extra.js  (by Hanzi)            SHARED
                 └─ audio         ← audio-index.js / TTS  (by text)         SHARED
```

- **`CHAR_INDEX`** (built in `app.js`) maps `Hanzi → full char object` (must have stroke
  data). Built from the school books + general library. The Library/series resolve each
  lesson's Hanzi through it; **characters with no bundled stroke data are dropped and
  `console.warn`-ed** — house rule: never show an unreadable character.
- **One source of truth per concern, shared by Hanzi.** Stroke data, radical info,
  enrichment and audio are all keyed by character/text, so a character that appears in
  several books is defined **once**. (See §6 on duplicates.)
- **Progress is per book** — `store.mastery["<bookId>:<Hanzi>"]`. Learning 人 in 中文 Book 1
  does NOT mark it learned in Band 1; each book's progress bar is independent. This is
  intentional and is what "manage the libraries properly" means here.
- `window.STUDIO` exposes helpers (`charIndex`, `extra`, `playAudio`, `makeWriter`,
  `gridSVG`, `medianPath`, `shuffle`, `palette`, …) for the exercise modules.

---

## 4. AUDIO — this is for you, Claude Code

Audio plays through a single hook, `playAudio(kind, key)` in `app.js`:

1. If `window.AUDIO_INDEX[kind][key]` is truthy → play `audio/<kind>/<key>.mp3`
   (filename URL-encoded automatically). On any play error it still falls back to TTS.
2. Otherwise → **browser text-to-speech**, `zh-CN`, preferring an installed Chinese voice.
3. If neither is available → a small "audio coming soon" toast.

`kind` ∈ `"char" | "word" | "sentence"`; `key` is the exact text (Hanzi, the word, or the
full sentence string incl. punctuation). Buttons already wired: big-character 🔊 (Learn
header), 词语 🔊, 句子 🔊, and the 听音选字 exercise auto-plays the character.

**The teacher will supply real recordings for characters, words AND sentences.** When they
arrive:
1. Drop files at `audio/char/人.mp3`, `audio/word/人口.mp3`,
   `audio/sentence/张口说"你好"。.mp3` (the app encodes the name; just save with the literal
   text as the base name, or generate the manifest from the folder).
2. Set the matching entries in `learn/audio-index.js` to `true` (or regenerate that file
   from the contents of `audio/`).
   Until a key is listed there, that item is **read aloud by the browser** — the app is
   fully usable with zero audio files today, and upgrades to real audio per-item with no
   code change.

> TTS quality/voice varies by device. The file path always wins when a recording exists.

---

## 5. CONTENT authoring (the main ongoing content task)

The display is complete; coverage is partial. Authoring more = editing two files.

### 5a. Radicals — `radicals.js` (already broad)
Keyed by the **base radical glyph**. Gives every character a radical name + English meaning
+ "Often about …" note **for free**. The app normalises a character's `radical` (stripping
any `" (…名…)"` the source tacked on) and looks it up. Add any missing radicals; format:
`"氵": { cn:"三点水", en:"water", note:"to do with water or liquid" }`.

### 5b. Per-character — `content-extra.js` (keyed by Hanzi)
```js
"好": {
  origin:  "…short, child-friendly memory story…",          // 小故事
  word:    { w:"你好", py:"nǐ hǎo", en:"hello" },             // 词语 + 组词 exercise
  sentence:{ seg:[["你","nǐ"],["好","hǎo"],["！",""]], en:"Hello!" }, // 句子 + 选字填空
  struct:  "lr"   // 结构 builder: single|lr|tb|lmr|tmb|sw|full
}
```
Rules: 组词 blanks the headword inside `word.w` (so it MUST contain the character); 选字填空
blanks it inside `sentence.seg` (so the char MUST appear in `seg`); each `seg` item is
`[char, pinyin]` with pinyin `""` for punctuation. **One ruby per character** is produced
automatically — keep that invariant (project rule §1). Anything missing is just hidden,
never broken; exercises that need data show **disabled with a reason** until you add it.

**Current coverage** (extend toward 100% of active books):
- radicals: ~all common radicals in the corpus · struct: ~100 · word: ~100
- origin (story): 42 · sentence: 28  ← **biggest gap; author these next**, starting with
  the active pilot (中文 Book 1 / Band 1), highest-frequency characters first.

---

## 6. LIBRARY — adding books & characters

Edit **`learn/library-data.js`**. Structure: `series[] → books[] → lessons[] → chars:[Hanzi]`.
A book's `id` is its **progress key — keep it stable**. Duplicates across books are fine
(content is shared by Hanzi; progress is per book). To add a new series, push another entry
to `series`; to add a volume, push to that series' `books`.

A character only appears if its stroke data is in `CHAR_INDEX`. To make a **new** character
listable, add its stroke data to `general-data.js` (or a school book):
1. Get makemeahanzi data from **`chanind/hanzi-writer-data`** → `data/<char>.json`
   (`{strokes:[…], medians:[…]}`, 1024 **Y-up** space = our `s`/`m`). The sandbox blocks
   non-ASCII paths — fetch via `github_read_file` or rename to codepoint-hex first.
2. Append `{ "ch":"的","py":"de","en":"(particle)","strokes":8,"radical":"白","s":[…],"m":[…] }`
   to a `general-data.js` group. It's now in `CHAR_INDEX` and listable anywhere.

### 中文 Book 1 — 45 characters still missing stroke data (complete the pilot)
```
L3 出 入 座 立      L4 地 父 母         L5 电 禾 金
L6 衣 车 瓜         L7 生 叫 岁 喜 欢 习  L8 的
L9 开 真 兴 见 老 师 们   L10 方 向 面 太 阳 个
L11 季 知 唱 叶      L12 新 到 闹 穿 戴 帽 祝 体
```
Add to `general-data.js`, then re-add each into its lesson's `chars` in `library-data.js`.
(99/144 present today.)

---

## 7. Exercises

`EXS[]` in `exercises.js` is the catalogue (id, skill, zh, en, desc, optional `need`).
`need` ∈ `word|sentence|struct|radical|s` gates availability via `qualifies()` and shows a
reason when locked. Skill labels/colours in `SKILL` (听/读/写). To add a type: add an `EXS`
entry, a `render…()`, and a `case` in `render()`'s dispatch.

- **Distractors are deliberately hard:** pinyin prefers the same initial; character/listen
  prefer the same **radical** (visually confusable); strokes use near counts.
- **结构 Structure builder** (teacher's idea, built as proposed): pinyin+meaning shown, char
  hidden → **pick the overall shape** (the scored, auto-graded step) → free-sketch each part
  in dashed regions → **Reveal & compare** overlays the real character (self-assessed).
- **描红 Trace** uses a **median-coverage** heuristic (% of target path covered, threshold
  60%) — an honest simple check, not true recognition. Real handwriting/stroke recognition
  for both is a future Claude-Code task.

---

## 8. UI conventions touched this round
- Learn stroke controls: **Colour + Order default ON**; speed control and the duplicate
  "Watch strokes" button removed; controls grouped into Replay/Step | Colour/Order, then
  Trace/Undo/Clear.
- Home: one unified `.bookcard`, grouped into `.hsec` series sections (school course / 中文 /
  General-by-theme). Adding a series or volume adds cards automatically.
- One `<ruby>` per character everywhere (project rule §1). Bump `studio.css?v=` after CSS
  edits (browsers cache hard).

---

## 9. Status / roadmap
| | |
|---|---|
| Learn = website model (radical meaning, story, word, sentence, audio) | ✅ display done; content partial (§5) |
| Stroke-control cleanup (defaults, remove speed/watch) | ✅ |
| Exercise Hub + 描红 / 结构 / 听音选字 / 组词 / 选字填空 / hard distractors | ✅ |
| Home unified & grouped by series → book | ✅ |
| Audio: file-or-TTS hook + manifest | ✅ (TTS now; drop files + flip manifest) |
| **Real audio** (char/word/sentence) | ⏳ teacher supplies → Claude Code wires (§4) |
| **Author stories + sentences** toward full coverage | ⏳ ongoing (§5b) |
| **Finish 中文 Book 1** (45 chars) + add more 中文 volumes | ⏳ (§6) |
| Real stroke/handwriting recognition for trace & structure | ⏳ future |
