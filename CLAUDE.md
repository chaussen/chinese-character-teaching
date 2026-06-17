# CLAUDE.md — Character Studio (学写字)

## Workflow — TRUNK-BASED (IMPORTANT)
- We **always work trunk-based**: develop and test **directly on `master`**, no feature
  branches. Commit and push straight to `master` (production testing happens on `master`).
- Do **not** create branches or pull requests unless explicitly asked.

## Project layout
- `learn/` — the web app (vanilla JS, self-contained data files):
  - `app-data.js` (`window.APP_DATA`) — the taught core, grouped band → unit (236 chars).
  - `general-data.js` (`window.GENERAL_DATA`) — General library, grouped by theme (~2986 chars).
  - `library-chars.js` (`window.LIBRARY_CHARS`) — stroke-data pool feeding the Library books.
  - `char-data.js` (`window.CHAR_DATA`) — 12 audited site chars with inline `ex`.
  - `content-extra.js` (`window.CONTENT_EXTRA`) — per-character enrichment keyed by Hanzi:
    `origin` (小故事), `word` (词语 example phrase), `sentence` (句子 example sentence), `struct`.
  - `audio-index.js` (`window.AUDIO_INDEX`) — AUTO-GENERATED manifest of which clips exist.
- `audio/{char,word,sentence}/<text>.mp3` — edge-tts recordings.
- `tools/build/` — content pipeline; `tools/generate_audio.py` — audio generator.

## Example phrases / sentences live in `content-extra.js`
The character data files carry no example fields — the LEARN page pulls
`word`/`sentence` from `CONTENT_EXTRA[ch]`. To add examples for a character, add an
entry there (keyed by the Hanzi).

### Content build pipeline (`tools/build/`)
1. `make_batches_all.py` — scans ALL collections, writes `content4/in_*.json` for every
   char missing `word`/`sentence`. (`make_batches.py` was the older, library-only version.)
2. Author `content<N>/out_*.json`: `{ "<ch>": {origin, word:{w,en}, sentence:{cn,en}} }`.
   Pinyin is computed by the assembler — do not hand-write it.
3. `assemble.py` — globs `content*/out_*.json`, computes pinyin (pypinyin) + `struct`
   (from `dictionary.txt`), and **merges** field-by-field into `content-extra.js`.
   - `dictionary.txt` is a gitignored makemeahanzi download:
     `curl -s https://cdn.jsdelivr.net/gh/skishore/makemeahanzi/dictionary.txt -o tools/build/dictionary.txt`

## Audio
`python3 tools/generate_audio.py` is **data-driven** and already covers examples: it
records `char`, `word` (`CONTENT_EXTRA[ch].word.w`) and `sentence` (joined seg text)
clips, then rebuilds `audio-index.js` from what's on disk. After adding new examples,
re-run it to fill the missing word/sentence audio (`--manifest-only` just rebuilds the index).
