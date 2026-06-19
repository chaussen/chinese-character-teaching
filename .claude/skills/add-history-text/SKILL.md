---
name: add-history-text
description: Add a new passage to the 史案 History Reader (history-reader/). Use when the user asks to add / fetch / ingest a 正史 text (梁书, 陈书, 魏书, …) or a 传/纪/卷 into the History Reader. Encodes WHAT annotation data the reader needs, HOW to build it, and WHERE to source each layer authoritatively.
---

# Add a text to the 史案 History Reader

A new passage is **far more annotation data than base text**. The base 正史 text is the
small part; the reader's value — and its work — is the *sourced annotation graph* layered
on top. This skill is the runbook for producing that graph reliably.

Read `history-reader/data.js` first (the live shape + the existing `ENTITIES` registry you
dedupe against) and the memory note `history-reader-app.md`.

## THE HARD RULE (do not violate)
Every annotation is **an assertion about history**. A wrong or fabricated one is worse than
none. Therefore:
- **`src` (溯源) is mandatory for any entity presented as fact.** If you cannot attach a real,
  checkable citation, set no `src` and the UI will mark it **未溯源** — never invent a
  plausible-looking citation (fake 卷号 / fake 《通典》 refs are the #1 failure mode).
- **`互见` (`seen`) must be verified** — only list a chapter if the entity genuinely appears
  there. Omit otherwise. Do not guess cross-references.
- **`今比` (现代类比) and map `xy` are interpretive, not sourced.** `今比` is an authored
  analogy; `xy` are schematic 0–100 layout coords, NOT geography. Never cite either as if sourced.

## Inputs to get from the user (ask if missing)
- **Which text** — 书名 + 传/纪/卷 (e.g. 《陈书·侯安都传》, 《梁书·武帝纪下》).
- **Span** — full 传 or a 节选; give start phrase → end phrase.
- Optional: `subject` (传主, for map/rel/rise headers), `depth` (e.g. "注解 only" for a minor
  passage — skip map/rel/rise), and any disputed points to flag (`alt`).

---

## WHAT to produce (the data inventory)

Per passage you build, into `history-reader/data.js` (append to `PASSAGES`; merge entities into
the shared `ENTITIES` registry — **dedupe by canonical id** so 互见 aggregates across texts):

1. **Base text** → `lines: []` — punctuated classical text, split by sentence/clause, with inline
   markers: `«entityId»` for a 知识层 专名, `⟨langId⟩` for a 语言层 token.
2. **ENTITIES** (global registry) — one record per 专名: `{ w, cat, brief, fields:[{k,v}], src, seen:[] }`.
   `cat ∈ person|place|office|era|rank`. Put the 现代类比 in a `今比` field (the dock leads with it).
3. **LANG tokens** — one per 语言层 word: `{ w, role, sub, roleFull, gloss, src }`. `role ∈
   句式|副词|活用|代词|介词`. `gloss` is the **context-specific** reading, not the whole dictionary entry.
4. **map** — `{ caption, points:[{id, order, xy:[0-100], mod(今地), note, alt?, ref?}], route:[id…] }`.
5. **rel** — `{ center:{w,sub}, nodes:[{id, w, rel, sub, xy:[0-100]}] }`.
6. **rise** — `[{ year, tag, rank:0-100, title, ref, note }]` (career / 时间轴; `rank` = office height).

---

## WHERE to source each layer (what / how / where)

Two kinds of source: **(F) fetchable** — pull the text *and* cite it; **(R) reference** — cite
even though not fully fetchable. Use WebFetch / WebSearch.

### Base text — (F)
- **维基文库** (primary): `https://zh.wikisource.org/wiki/<书名>/卷<N>` — e.g.
  `https://zh.wikisource.org/wiki/梁書/卷56` (侯景传). Full 二十四史, usually punctuated.
- **Chinese Text Project (ctext.org)** (cross-check): has the 正史 under 史部; good for variant
  checking and for the 工具書 below.
- **Kanripo** `kanripo.org` (KR2 史部) — third cross-check.
- Normalize: keep 繁体, fix 异体字/OCR slips, keep punctuation. Note edition caveat: the
  authoritative **中華書局 點校本** has *editorial* copyright on punctuation/collation — use the
  free copies' wording but cite the 點校本 as the canonical base.

### 人物 (person) fields — (F/R)
身份/生卒/大事/关系. Source: the figure's **本传** (the 正史 itself) + **《资治通鉴》** (F:
ctext / 维基文库) for dates & narrative; cross-check **《漢語大詞典》/《中国历史人物辞典》** (R).
`src` → the 本传 卷 or 《资治通鉴·X纪》.

### 地名 (place) fields — (F)
今地/沿革/形胜/辨. Source, in order: **《读史方舆纪要》**(顾祖禹) and **《元和郡县图志》**(李吉甫) —
both on ctext.org / 维基文库 — for 沿革/形胜; **《通典·州郡》** for 政区. `src` → the specific 卷.
For **modern 今地** and the 辨 (disputed籍贯/治所) note both readings (`alt:true`).

### 官职 (office) fields — (F)
性质/职权/品级/今比. Source: **《通典·职官》**(杜佑, F: `https://ctext.org/tongdian` / 维基文库) —
the primary authority for 北朝/隋唐 官制; plus **《历代职官表》** (R). `src` → 《通典·职官·…》.
`今比` is your authored analogy (not cited).

### 年号 (era) fields — (F)
公元/在位/大事. Source: the corresponding **帝纪** (本史) + a **中国历史纪年表** (R) for the 公元
conversion; **《资治通鉴》** for 是年大事. `src` → 《X书·X帝纪》.

### 爵位 (rank) fields — (F)
爵等/封地/意味. Source: **《通典·职官·封爵》** and **《隋书·百官志》/《魏书·官氏志》** 爵制 (F). `src`
→ the specific 志.

### 语言层 LANG (grammar) — (R + F)
context gloss. Source: **王力《古代汉语》** (被动句 / 词类活用 / 虚词通论) → the standard `src`
for 句式/活用; **《古汉语虚词词典》** for 虚词 (之/以/其/见…); **《古汉语常用字字典》** for 古今异义
(e.g. 稍=渐渐). **漢典 (zdic.net)** `https://www.zdic.net/hans/<字>` is fetchable (aggregates
古代漢語詞典/康熙字典) to confirm a reading. Write the gloss **for this sentence**, then cite.

### map coordinates — (R, interpretive)
`xy` are **schematic only** right now (layout, 0–100). Real county-level coords come from
**谭其骧《中国历史地图集》** and the digital **CHGIS** (China Historical GIS, 复旦/Harvard:
`https://chgis.fudan.edu.cn`) — note these as the production geodata source. Keep the caption's
"底图待接入真实地理坐标" until a real basemap is wired. Modern equivalents (`mod`) come from the
地名 sources above.

### 互见 `seen` (cross-references) — (F, verify each)
Which other 传/史 the entity appears in. Until the cross-text engine exists, **verify by
searching** (ctext full-text search, 维基文库) that the entity actually appears in each chapter
you list. Prefer the most relevant 3–4. Omit unverifiable ones.

---

## HOW (procedure)

1. **Confirm inputs** (text, span, subject). Read `history-reader/data.js`.
2. **Fetch base text** from 维基文库 (cross-check ctext). Trim to the span; clean & punctuate.
3. **Identify markers**: tag 专名 (人/地/官/年/爵) → `«id»`; tag 虚词/活用/句式 → `⟨id⟩`. Choose
   stable lowercase ids; **reuse existing registry ids** for recurring entities (this is the dedup
   that powers 互见).
4. **Build ENTITIES** — for each new 专名, fetch/cite per the WHERE table; attach `src` or leave
   未溯源; add verified `seen`. Add `今比` for office/place where a modern analogy clarifies.
5. **Build LANG tokens** — context gloss + grammar `src`.
6. **Build map / rel / rise** (skip per `depth`). `xy` schematic; `rank` for 时间轴 height; `ref`
   links nodes to entity cards.
7. **Wire in**: append the passage object to `PASSAGES`, merge new entities/lang into the registry.
   (When `data.js` gets unwieldy with several texts, split to `history-reader/content/<id>.json`
   + a small assembler that writes `data.js`, mirroring `tools/build/assemble.py` → `content-extra.js`.
   Set that up the first time a second text makes the single file painful.)
8. **Verify** (see below).
9. **Trust pass**: list every **未溯源** entity and any inferred date/coord/互见 so the user can
   spot-check before commit.
10. **Commit** to `master` (trunk-based) when the user approves.

## Verify (headless)
```bash
cd history-reader
python3 -m http.server 8731 >/tmp/shi.log 2>&1 & SRV=$!
sleep 1
chromium --headless --no-sandbox --disable-gpu --virtual-time-budget=4000 \
  --dump-dom http://localhost:8731/ 2>/dev/null | \
  grep -cE 'class="ncard"|data-act="selTerm"'   # cards + clickable terms render
kill $SRV
```
Also `node --check data.js`. Confirm: new passage's terms appear in 注解, marks render in text,
selecting each opens the dock (term → 现代类比 + fields + 溯源/未溯源 + 互见; lang → gloss),
and 地图/关系/时间轴/升迁/专名库 populate. (For deeper checks, reuse the click-driven harness
pattern from the build session.)

## Pre-commit checklist
- [ ] No fabricated `src`; everything uncited is visibly `未溯源`.
- [ ] Recurring entities reuse existing registry ids (互见 dedupes across texts).
- [ ] Every `seen` chapter verified to actually contain the entity.
- [ ] `今比` / `xy` not presented as sourced facts; disputed sites flagged `alt:true`.
- [ ] `node --check` clean + headless render shows the new passage end-to-end.
- [ ] 未溯源 / inferred items surfaced to the user for the trust pass.
