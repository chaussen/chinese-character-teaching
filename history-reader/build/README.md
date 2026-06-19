# 史案 content pipeline (`build/`)

A **cache-backed pipeline** for adding passages to the History Reader. It splits the
work into the deterministic half (this pipeline) and the irreducible AI half (sourcing
+ interpretation, run via the `add-history-text` skill).

`data.js` is now **generated**. Edit the cache/content under `build/`, then assemble.

## The cache (source of truth)

```
build/
  registry/
    meta.json       CATS + LANG_ROLES (presentation config)
    entities.json   global entity registry — the CACHE. Canonical id → record
                    {w,cat,brief,fields[],src,seen[]}. Dedupes across every text.
    lang.json       language-token registry — per-context glosses {w,role,sub,gloss,src}.
  content/
    <id>.json       one passage each: {id,title,sub,seal,subject,intro,lines[],map,rel,rise}.
                    lines reference the registry inline: «entityId|surface» · ⟨langId|surface⟩.
    _order.json     passage order (the collection is ordered; keep this in sync).
  input/
    <id>.txt        raw paste-in text (+ optional front-matter). Ingest reads from here.
```

Why a cache: every sourced fact (an entity's fields + `src`, a gloss) is **stable and
reusable** — 侯景 sourced once is reused in every text he appears in (his `seen`
aggregates them). So reasoning is paid once per entity, not per text; coverage grows,
the AI residue shrinks.

## Scripts

| Command | Does |
|---|---|
| `python3 build/ingest.py input/<id>.txt` | **Deterministic.** Segment text into lines, auto-link every entity already in the cache (`«id\|surface»`), emit `content/<id>.json` skeleton + `input/<id>.residue.md` (the AI-half checklist). Invents nothing. |
| `python3 build/validate.py` | Structural + referential integrity: every marker/route/ref resolves, coords sane, records well-formed. **Errors block; warnings = the 未溯源 trust-pass surface.** |
| `python3 build/assemble.py` | Validate, then regenerate `history-reader/data.js`. Refuses on any error. |
| `python3 build/assemble.py --check` | CI/pre-commit: exit non-zero if `data.js` is out of date. |

## Workflow: adding a text

1. **Paste** the 正史 text into `build/input/<id>.txt`, with front-matter:
   ```
   # id: houan-chenshu
   # title: 陳書·侯安都傳
   # sub: 节选 · 唐 · 姚思廉 撰
   # subject: 侯安都
   # intro: 一段导读…
   ---
   <classical text…>
   ```
2. **Ingest** → `python3 build/ingest.py input/houan-chenshu.txt`. Known entities are
   already linked; read `input/<id>.residue.md`.
3. **AI half** (`add-history-text` skill) — the part a script can't do safely:
   - review line segmentation;
   - for each *new* entity in the residue, add a record to `registry/entities.json`
     with a **real `src`** (or leave it 未溯源 — never fabricate a citation);
   - tag the language layer ⟨id⟩ into `registry/lang.json` (per-context glosses);
   - author `map` / `rel` / `rise` in the content file;
   - add the id to `content/_order.json`.
4. **Validate** → `python3 build/validate.py`. Resolve every error; review warnings
   (未溯源 / interpretive fields) as the trust pass.
5. **Assemble** → `python3 build/assemble.py` (regenerates `data.js`).
6. **Verify** the reader renders (see `add-history-text` skill's headless check), then
   commit to `master`.

## What's deterministic vs. AI

- **Script:** fetch/clean, segment, auto-link cached entities, assemble, validate, render-check.
- **AI (irreducible):** referent identification, sense/period selection, conflict
  resolution, **citation correctness**, and authored fields (`今比`, rel, rise). Each is
  an assertion about history — sourced or visibly 未溯源, never fabricated. Its output is
  written back into the cache, so it's never recomputed.
