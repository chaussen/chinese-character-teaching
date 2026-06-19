#!/usr/bin/env python3
"""Ingest a raw 正史 passage into a content skeleton — the deterministic half.

Drop a text into build/input/<id>.txt (optional `# key: value` front-matter, then
a `---` line, then the classical text). This does the MECHANICAL pass:

  • split the text into lines (approximate — the AI/you refine boundaries),
  • auto-link every 专名 already in the entity registry (the CACHE) by surface
    match, reusing canonical ids and emitting «id|surface» overrides,
  • emit content/<id>.json skeleton,
  • write input/<id>.residue.md: what the AI half must still do (new entities to
    source, language tokens, map/rel/rise) + which links to verify.

It NEVER invents facts. Language tokens (⟨⟩) are per-context and are left for the
AI half; only registry entities are auto-linked. If content/<id>.json already
exists, the skeleton is written alongside as <id>.skel.json so AI edits are safe.

Usage:  python3 build/ingest.py input/<id>.txt
"""
import json, re, sys, pathlib
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
REG, CON, INP = HERE / 'registry', HERE / 'content', HERE / 'input'

HAN = r'㐀-鿿'
HAN_RUN = re.compile(f'[{HAN}]+')
MARK_ENT = re.compile(r'«([^»]+)»')
OPEN, CLOSE, TERM = set('「『“'), set('」』”'), set('。！？')


def parse_input(path):
    """Return (meta dict, body text). Front-matter = leading `# k: v` lines to `---`."""
    raw = path.read_text(encoding='utf-8')
    meta, body = {}, raw
    if raw.lstrip().startswith('#'):
        head, _, rest = raw.partition('\n---')
        for ln in head.splitlines():
            ln = ln.strip()
            if ln.startswith('#') and ':' in ln:
                k, v = ln[1:].split(':', 1)
                meta[k.strip()] = v.strip()
        body = rest if _ else raw
    return meta, body


def segment(body):
    """Split into sentence-ish lines. Won't break inside 「」/『』 quotes; trailing
    closers/terminators stay attached. Approximate by design — AI reviews breaks."""
    text = re.sub(r'\s+', '', body)
    lines, buf, depth = [], [], 0
    for ch in text:
        buf.append(ch)
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth = max(0, depth - 1)
        elif ch in TERM and depth == 0:
            lines.append(''.join(buf))
            buf = []
    if buf:
        lines.append(''.join(buf))
    return [ln for ln in lines if ln]


def alias_index():
    """Surface → entity id, harvested from the cache: every entity's `w` plus every
    «id|surface» override already used in shipped content. Multi-char only (single
    chars are too ambiguous to auto-link; they're reported as residue instead)."""
    entities = json.loads((REG / 'entities.json').read_text(encoding='utf-8'))
    idx = {}
    def add(surface, eid):
        if len(surface) >= 2:
            idx.setdefault(surface, eid)
    for eid, e in entities.items():
        add(e.get('w', ''), eid)
    for f in CON.glob('*.json'):
        if f.name == '_order.json':
            continue
        for line in json.loads(f.read_text(encoding='utf-8')).get('lines', []):
            for tok in MARK_ENT.findall(line):
                parts = tok.split('|', 1)
                if len(parts) == 2:
                    add(parts[1], parts[0])
    return entities, idx


def autolink(line, idx, entities, linked):
    """Greedy longest-match, non-overlapping. Emit «id» or «id|surface»."""
    surfaces = sorted(idx, key=len, reverse=True)
    out, i, n = [], 0, len(line)
    while i < n:
        hit = next((s for s in surfaces if line.startswith(s, i)), None)
        if hit:
            eid = idx[hit]
            canon = entities[eid].get('w', '')
            out.append(f'«{eid}»' if hit == canon else f'«{eid}|{hit}»')
            linked[eid] += 1
            i += len(hit)
        else:
            out.append(line[i])
            i += 1
    return ''.join(out)


def residue(pid, meta, lines, linked, entities, idx):
    covered = set()
    for s in idx:
        covered.update(s)
    # candidate new proper nouns: multi-char Han runs not (fully) made of linked chars
    runs = Counter()
    for ln in lines:
        for m in HAN_RUN.findall(MARK_ENT.sub('', ln)):
            for L in (2, 3):
                for k in range(len(m) - L + 1):
                    runs[m[k:k + L]] += 1
    cand = [(g, c) for g, c in runs.items() if c >= 2 and not all(ch in covered for ch in g)]
    cand.sort(key=lambda x: (-x[1], -len(x[0])))

    lk = '\n'.join(f'- `{eid}` ({entities[eid].get("w","?")}) ×{n}'
                   for eid, n in sorted(linked.items(), key=lambda x: -x[1])) or '- (none)'
    cd = '\n'.join(f'- {g} ×{c}' for g, c in cand[:30]) or '- (none flagged)'
    return f"""# Ingest residue · {pid}

Mechanical pass done. The items below are the **AI half** — each is an assertion
about history, so source it (`src`) or leave it 未溯源. Do not fabricate citations.

## Meta ({'from front-matter' if meta else 'MISSING — fill in content/'+pid+'.json'})
{json.dumps(meta, ensure_ascii=False, indent=2) if meta else '(none provided)'}

## Auto-linked entities (VERIFY each is the right referent in context)
{lk}

## New-entity candidates (recurring multi-char runs not in the registry)
Scan for 人名/地名/官名/年号/爵位 to add to registry/entities.json (with `src`):
{cd}

## Still to author (the irreducible reasoning)
- [ ] Review line segmentation (quotes/dialogue may have merged).
- [ ] Tag language layer ⟨id⟩ — 句式/活用/虚词 — add per-context records to registry/lang.json.
- [ ] New entities → registry/entities.json: w, cat, brief, fields[], `src`, verified `seen`.
- [ ] map: points[{{id,order,ll:[lng,lat],mod,note}}] + route; rel: center+nodes; rise: timeline.
- [ ] Add `{pid}` to content/_order.json.
- [ ] Run `python3 build/validate.py` then `python3 build/assemble.py`.
"""


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python3 build/ingest.py input/<id>.txt')
    src = pathlib.Path(sys.argv[1])
    if not src.is_absolute():
        src = (HERE / src) if (HERE / src).exists() else (pathlib.Path.cwd() / src)
    meta, body = parse_input(src)
    pid = meta.get('id') or src.stem

    entities, idx = alias_index()
    linked = Counter()
    lines = [autolink(ln, idx, entities, linked) for ln in segment(body)]

    skel = {
        'id': pid,
        'title': meta.get('title', f'TODO 书名·传名 ({pid})'),
        'sub': meta.get('sub', 'TODO 节选 / 撰者'),
        'seal': meta.get('seal', (meta.get('subject', '？') or '？')[0]),
        'subject': meta.get('subject', 'TODO 传主'),
        'intro': meta.get('intro', 'TODO 一段导读'),
        'lines': lines,
        '_todo': 'See input/%s.residue.md. map/rel/rise omitted until authored.' % pid,
    }

    dest = CON / f'{pid}.json'
    if dest.exists():
        dest = INP / f'{pid}.skel.json'
        note = f'content/{pid}.json exists — wrote skeleton to {dest.relative_to(HERE)} (merge by hand to keep AI edits)'
    else:
        note = f'wrote {dest.relative_to(HERE)}'
    dest.write_text(json.dumps(skel, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    res = INP / f'{pid}.residue.md'
    res.write_text(residue(pid, meta, lines, linked, entities, idx), encoding='utf-8')

    print(f'ingest [{pid}]: {len(lines)} lines, {len(linked)} entity-link(s) '
          f'({sum(linked.values())} hits) from registry cache.')
    print(' ', note)
    print(f'  residue → {res.relative_to(HERE)}  (the AI-half checklist)')


if __name__ == '__main__':
    main()
