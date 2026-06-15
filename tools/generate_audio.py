#!/usr/bin/env python3
"""Generate edge-tts audio for Character Studio (学写字).

DATA-DRIVEN — nothing is hardcoded. The script scans the app's own data files
in learn/ for every character, word and sentence the app can play, so adding
new characters/content and re-running just fills in the new clips.

Sources (see "Character Studio - HANDOFF.md" §4):
    char      every `ch` in learn/app-data.js + learn/general-data.js  (= CHAR_INDEX)
    word      every CONTENT_EXTRA[ch].word.w        in learn/content-extra.js
    sentence  every CONTENT_EXTRA[ch].sentence      (joined seg text)

Writes literal-text filenames (the app URL-encodes them at request time):
    audio/char/人.mp3   audio/word/人口.mp3   audio/sentence/张口说"你好"。.mp3
then regenerates learn/audio-index.js from whatever is actually on disk, so the
app upgrades from browser TTS to the real recording, per item, automatically.

Usage (venv with edge-tts active — `enter` then):
    python3 tools/generate_audio.py                 # fill in missing files only
    python3 tools/generate_audio.py --force         # re-record everything
    python3 tools/generate_audio.py --voice zh-CN-YunxiNeural
    python3 tools/generate_audio.py --manifest-only # just rebuild audio-index.js
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
LEARN = ROOT / "learn"
AUDIO = ROOT / "audio"
KINDS = ("char", "word", "sentence")
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # clear, friendly female zh-CN voice


def load_window_json(path):
    """Return the object assigned to `window.X = {...};` in a data file, or None.

    The curriculum/library/enrichment files are JSON.stringify output, so the
    right-hand side is strict JSON once the `window.X =` wrapper and `;` are gone.
    """
    if not path.exists():
        print(f"  (skip — not found: {path.relative_to(ROOT)})", file=sys.stderr)
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*", text)
    if not m:
        print(f"  (skip — no window.X assignment: {path.name})", file=sys.stderr)
        return None
    body = text[m.end():].rstrip().rstrip(";").rstrip()
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        print(f"  (skip — {path.name} is not strict JSON: {e})", file=sys.stderr)
        return None


def collect():
    """Build {kind: set(text)} of every clip the app may play."""
    want = {k: set() for k in KINDS}

    # characters: every taught/library char carries stroke data → it is playable
    app = load_window_json(LEARN / "app-data.js") or {}
    for band in app.get("bands", []):
        for unit in band.get("units", []):
            for c in unit.get("chars", []):
                if c.get("ch"):
                    want["char"].add(c["ch"])

    gen = load_window_json(LEARN / "general-data.js") or {}
    for group in gen.get("groups", []):
        for c in group.get("chars", []):
            if c.get("ch"):
                want["char"].add(c["ch"])

    # stroke-data-only pool feeding the Library books (library-chars.js)
    lib = load_window_json(LEARN / "library-chars.js") or {}
    for c in lib.get("chars", []):
        if c.get("ch"):
            want["char"].add(c["ch"])

    # words + sentences: per-character enrichment, keyed by Hanzi
    extra = load_window_json(LEARN / "content-extra.js") or {}
    for ch, x in extra.items():
        if ch:
            want["char"].add(ch)
        w = (x or {}).get("word")
        if w and w.get("w"):
            want["word"].add(w["w"])
        s = (x or {}).get("sentence")
        if s and s.get("seg"):
            sentence = "".join(seg[0] for seg in s["seg"] if seg and seg[0])
            if sentence:
                want["sentence"].add(sentence)

    return want


def target_path(kind, text):
    return AUDIO / kind / f"{text}.mp3"


PER_CLIP_TIMEOUT = 25   # seconds before we give up on one request and retry
MAX_TRIES = 4           # edge-tts intermittently returns no audio on short text


async def _save_once(text, voice, tmp):
    """One synthesis attempt, bounded so a stalled request can't hang the run."""
    tmp.unlink(missing_ok=True)
    await asyncio.wait_for(edge_tts.Communicate(text, voice).save(str(tmp)), PER_CLIP_TIMEOUT)
    if tmp.stat().st_size == 0:               # service returned no audio
        raise RuntimeError("empty audio")


async def synth(text, kind, voice, sem, force, results):
    path = target_path(kind, text)
    if "/" in text or "\0" in text:  # would break the filesystem path
        results["skipped"].append((kind, text))
        print(f"  ! {kind:8} skipped (unsafe name): {text!r}", file=sys.stderr)
        return
    if path.exists() and not force:
        results["exists"] += 1
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    async with sem:
        last = None
        for attempt in range(1, MAX_TRIES + 1):
            try:
                await _save_once(text, voice, tmp)
                tmp.replace(path)  # atomic — a partial write never looks "done"
                results["made"].append((kind, text))
                print(f"  ✓ {kind:8} {text}")
                return
            except (Exception, asyncio.TimeoutError) as e:  # noqa: BLE001
                last = e
                if attempt < MAX_TRIES:
                    await asyncio.sleep(1.5 * attempt)  # back off, then retry
        tmp.unlink(missing_ok=True)
        results["failed"].append((kind, text, str(last)))
        print(f"  ✗ {kind:8} {text}  ({last})", file=sys.stderr)


async def run(want, voice, force, concurrency):
    sem = asyncio.Semaphore(concurrency)
    results = {"made": [], "exists": 0, "failed": [], "skipped": []}
    tasks = [
        synth(text, kind, voice, sem, force, results)
        for kind in KINDS
        for text in sorted(want[kind])
    ]
    await asyncio.gather(*tasks)
    return results


MANIFEST_HEADER = """\
/* audio-index.js — 学写字 · Character Studio · audio manifest.
   ▸ AUTO-GENERATED by tools/generate_audio.py from the contents of audio/.
     Do not edit by hand — re-run the generator instead. Listing a key here
     tells the app a real recording exists; everything else falls back to the
     browser's zh-CN text-to-speech (see playAudio in app.js). */
"""


def write_manifest():
    """Regenerate learn/audio-index.js from the files actually on disk."""
    index = {k: {} for k in KINDS}
    counts = {}
    for k in KINDS:
        d = AUDIO / k
        if d.is_dir():
            for f in sorted(d.glob("*.mp3")):
                index[k][f.stem] = True
        counts[k] = len(index[k])
    body = json.dumps(index, ensure_ascii=False, indent=2)
    (LEARN / "audio-index.js").write_text(
        MANIFEST_HEADER + "window.AUDIO_INDEX = " + body + ";\n", encoding="utf-8"
    )
    return counts


def main():
    ap = argparse.ArgumentParser(description="Generate Character Studio audio with edge-tts.")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help=f"edge-tts voice (default {DEFAULT_VOICE})")
    ap.add_argument("--force", action="store_true", help="re-record clips that already exist")
    ap.add_argument("--concurrency", type=int, default=6, help="parallel TTS requests (default 6)")
    ap.add_argument("--manifest-only", action="store_true", help="only rebuild audio-index.js from disk")
    args = ap.parse_args()

    if args.manifest_only:
        counts = write_manifest()
        print(f"Manifest rebuilt: " + ", ".join(f"{c} {k}" for k, c in counts.items()))
        return

    want = collect()
    total = sum(len(v) for v in want.values())
    print(f"Discovered {total} clips to ensure: "
          + ", ".join(f"{len(want[k])} {k}" for k in KINDS))
    print(f"Voice: {args.voice} · concurrency {args.concurrency} · "
          + ("re-recording all" if args.force else "only missing"))

    results = asyncio.run(run(want, args.voice, args.force, args.concurrency))

    counts = write_manifest()
    print("\nDone.")
    print(f"  made    {len(results['made'])}")
    print(f"  existed {results['exists']}")
    if results["skipped"]:
        print(f"  skipped {len(results['skipped'])} (unsafe filenames)")
    if results["failed"]:
        print(f"  FAILED  {len(results['failed'])} — re-run to retry:")
        for kind, text, err in results["failed"][:20]:
            print(f"            {kind} {text}: {err}")
    print("  manifest: " + ", ".join(f"{c} {k}" for k, c in counts.items()))


if __name__ == "__main__":
    main()
