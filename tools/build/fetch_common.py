#!/usr/bin/env python3
"""Fetch stroke data for the most common characters missing from the app's
pool and stage them in tools/build/common_pool.json.

Sources (both reachable from the web sandbox via jsdelivr):
  • stroke paths/medians : hanzi-writer-data@2.0 (makemeahanzi, 1024 Y-up)
  • pinyin / gloss / radical : skishore/makemeahanzi dictionary.txt

Frequency order comes from chinese_tools/data/common_characters.txt. Every
single Han character in that list that is not already in CHAR_INDEX
(app-data.js / general-data.js / library-chars.js) is fetched into the staging
pool, which tools/build/expand_general.py then groups by theme and embeds into
learn/general-data.js. The staging file is a build input only — the browser
never loads it — so the app ships each glyph's stroke data exactly once.

No audio is produced here (run tools/generate_audio.py on a machine with open
network for that); new chars fall back to browser TTS until then.

Usage:  python3 tools/build/fetch_common.py [--limit N]
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CTX = ssl.create_default_context(cafile="/etc/ssl/certs/ca-certificates.crt")
STROKE_CDN = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/"
DICT_URL = "https://cdn.jsdelivr.net/gh/skishore/makemeahanzi/dictionary.txt"
DICT_PATH = os.path.join(ROOT, "tools/build/dictionary.txt")
FREQ_PATH = os.path.join(ROOT, "chinese_tools/data/common_characters.txt")
POOL_PATH = os.path.join(ROOT, "tools/build/common_pool.json")


def get(url, timeout=30):
    last = None
    for _ in range(4):
        try:
            return urllib.request.urlopen(url, context=CTX, timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def load_dict():
    if not os.path.exists(DICT_PATH):
        print("downloading makemeahanzi dictionary…")
        open(DICT_PATH, "wb").write(get(DICT_URL, timeout=60))
    d = {}
    for line in open(DICT_PATH, encoding="utf-8"):
        line = line.strip()
        if line:
            o = json.loads(line)
            d[o["character"]] = o
    return d


def short_en(defn):
    if not defn:
        return ""
    s = re.sub(r"\s+", " ", defn.split(";")[0].strip())
    return s[:42].rsplit(" ", 1)[0] + "…" if len(s) > 42 else s


def have_chars():
    have = set()
    for p in ("learn/app-data.js", "learn/general-data.js", "learn/library-chars.js"):
        txt = open(os.path.join(ROOT, p), encoding="utf-8").read()
        have |= set(re.findall(r'"ch"\s*:\s*"(.)"', txt))
    return have


def ranked_singles():
    out, seen = [], set()
    han = re.compile(r"[一-鿿]")
    for line in open(FREQ_PATH, encoding="utf-8"):
        p = line.split()
        if len(p) >= 2 and len(p[1]) == 1 and han.match(p[1]) and p[1] not in seen:
            seen.add(p[1])
            out.append(p[1])
    return out


def fetch_strokes(ch):
    return json.loads(get(STROKE_CDN + urllib.parse.quote(ch) + ".json"))


def load_pool():
    if os.path.exists(POOL_PATH):
        return json.loads(open(POOL_PATH, encoding="utf-8").read())
    return {"chars": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap on chars to add (0 = all)")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    DICT = load_dict()
    have = have_chars()
    todo = [c for c in ranked_singles() if c not in have]
    if args.limit:
        todo = todo[: args.limit]
    print(f"have={len(have)}  to-fetch={len(todo)}")

    out, fails = {}, []

    def work(ch):
        g = fetch_strokes(ch)
        m = DICT.get(ch, {})
        return ch, {
            "ch": ch,
            "py": (m.get("pinyin") or [""])[0],
            "en": short_en(m.get("definition", "")),
            "strokes": len(g["strokes"]),
            "radical": m.get("radical", ""),
            "s": g["strokes"],
            "m": g["medians"],
        }

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, c): c for c in todo}
        for i, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                ch, rec = f.result()
                out[ch] = rec
            except Exception as e:  # noqa: BLE001
                fails.append((c, str(e)))
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}  (ok={len(out)} fail={len(fails)})")

    print(f"done: {len(out)} ok, {len(fails)} failed")
    if fails:
        print("  failed:", "".join(c for c, _ in fails))

    data = load_pool()
    existing = {c["ch"] for c in data["chars"]}
    # preserve frequency order, skip any that slipped into the pool meanwhile
    added = [out[c] for c in todo if c in out and c not in existing]
    data["chars"].extend(added)
    open(POOL_PATH, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
    print(f"merged {len(added)} chars → common_pool.json now {len(data['chars'])} chars")


if __name__ == "__main__":
    main()
