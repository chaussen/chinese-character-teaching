#!/usr/bin/env python3
"""Write content batches for EVERY character (all collections) that is still
missing an example phrase (词语 word) or example sentence (句子) in
learn/content-extra.js.

Unlike the older make_batches.py (library-chars only), this scans the union of
all data files the app ships — app-data.js, general-data.js, library-chars.js,
char-data.js — so no character is left without examples.

Output: tools/build/content4/in_*.json  (batches of <=B), feeding assemble.py.
"""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEARN = os.path.join(ROOT, 'learn')


def load_window_json(name):
    text = open(os.path.join(LEARN, name), encoding='utf-8').read()
    m = re.search(r'window\.\w+\s*=\s*', text)
    body = text[m.end():].rstrip().rstrip(';').rstrip()
    return json.loads(body)


# --- gather every character + its best-known py/en/radical -----------------
meta = {}  # ch -> {py,en,radical}
def note(c):
    ch = c.get('ch')
    if not ch:
        return
    meta.setdefault(ch, {})
    m = meta[ch]
    m.setdefault('py', c.get('py', ''))
    m.setdefault('en', c.get('en', ''))
    m.setdefault('radical', c.get('radical', ''))

app = load_window_json('app-data.js')
for b in app.get('bands', []):
    for u in b.get('units', []):
        for c in u.get('chars', []):
            note(c)
gen = load_window_json('general-data.js')
for g in gen.get('groups', []):
    for c in g.get('chars', []):
        note(c)
lib = load_window_json('library-chars.js')
for c in lib.get('chars', []):
    note(c)
chd = load_window_json('char-data.js') if os.path.exists(os.path.join(LEARN, 'char-data.js')) else []
for c in chd:
    note(c)

# --- what already has word AND sentence? ------------------------------------
ce = load_window_json('content-extra.js')
have_word = {ch for ch, v in ce.items() if (v or {}).get('word')}
have_sent = {ch for ch, v in ce.items() if (v or {}).get('sentence')}
# CHAR_DATA carries inline `ex` (an example sentence) — count it as a sentence.
inline_ex = {c['ch'] for c in chd if c.get('ex')}

# --- decomposition / etymology hint for nicer origins -----------------------
DICT = {}
dpath = os.path.join(ROOT, 'tools/build/dictionary.txt')
if os.path.exists(dpath):
    for line in open(dpath, encoding='utf-8'):
        line = line.strip()
        if line:
            o = json.loads(line); DICT[o['character']] = o

items = []
for ch in sorted(meta):
    need_word = ch not in have_word
    need_sent = ch not in have_sent and ch not in inline_ex
    if not (need_word or need_sent):
        continue
    m = meta[ch]
    ety = (DICT.get(ch, {}) or {}).get('etymology') or {}
    items.append({
        'ch': ch, 'py': m['py'], 'en': m['en'], 'radical': m['radical'],
        'decomp': DICT.get(ch, {}).get('decomposition', ''),
        'hint': ety.get('hint', ''), 'etype': ety.get('type', ''),
        'need_word': need_word, 'need_sentence': need_sent,
    })

print('characters needing examples:', len(items))
outdir = os.path.join(ROOT, 'tools/build/content4')
os.makedirs(outdir, exist_ok=True)
B = 50
batches = [items[i:i + B] for i in range(0, len(items), B)]
for i, b in enumerate(batches, 1):
    json.dump(b, open(os.path.join(outdir, f'in_{i:02d}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
print('wrote', len(batches), 'batch files of <=', B, 'to content4/')
