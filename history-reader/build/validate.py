#!/usr/bin/env python3
"""Structural + referential validation for the 史案 data cache.

The trust contract (see add-history-text skill) lives here as machine checks:
  - ERRORS break the build (broken refs, malformed records, bad coords).
  - WARNINGS are the human trust-pass surface — chiefly 未溯源 (no `src`) and
    interpretive/uncited fields. They never block; they get listed for review.

Run standalone:   python3 build/validate.py
Imported by:      assemble.py (build is refused if there are ERRORS).
"""
import json, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
REG, CON = ROOT / 'registry', ROOT / 'content'

# China-proper bbox — a generous sanity window for 县级 lng/lat, NOT a precise fence.
LNG, LAT = (70.0, 140.0), (15.0, 55.0)

MARK_ENT = re.compile(r'«([^»]+)»')   # «id» or «id|surface»  (知识层 专名)
MARK_LNG = re.compile(r'⟨([^⟩]+)⟩')   # ⟨id⟩ or ⟨id|surface⟩  (语言层 token)


def _id(token):
    return token.split('|', 1)[0]


def load():
    """Read the cache + content off disk into one dict. Raises on bad JSON."""
    meta = json.loads((REG / 'meta.json').read_text(encoding='utf-8'))
    entities = json.loads((REG / 'entities.json').read_text(encoding='utf-8'))
    lang = json.loads((REG / 'lang.json').read_text(encoding='utf-8'))
    order = json.loads((CON / '_order.json').read_text(encoding='utf-8'))
    passages = {}
    for f in sorted(CON.glob('*.json')):
        if f.name == '_order.json':
            continue
        passages[f.stem] = json.loads(f.read_text(encoding='utf-8'))
    return dict(meta=meta, entities=entities, lang=lang, order=order, passages=passages)


def check(data):
    """Return (errors, warnings) as lists of strings. Pure; no I/O."""
    errors, warnings = [], []
    meta, ents, lang = data['meta'], data['entities'], data['lang']
    order, passages = data['order'], data['passages']
    cats = set(meta.get('CATS', {}))
    roles = set(meta.get('LANG_ROLES', {}))

    if not cats:
        errors.append('meta.json: CATS missing/empty')
    if not roles:
        errors.append('meta.json: LANG_ROLES missing/empty')

    # ── entity registry ──
    for eid, e in ents.items():
        where = f'entity[{eid}]'
        for k in ('w', 'cat', 'brief'):
            if not e.get(k):
                errors.append(f'{where}: missing `{k}`')
        if e.get('cat') and e['cat'] not in cats:
            errors.append(f"{where}: cat '{e['cat']}' not in CATS {sorted(cats)}")
        if not e.get('src'):
            warnings.append(f'{where} ({e.get("w","?")}): 未溯源 — no `src`')
        for s in e.get('seen', []):
            if not isinstance(s, str):
                errors.append(f'{where}: `seen` entry not a string: {s!r}')

    # ── language tokens ──
    for lid, t in lang.items():
        where = f'lang[{lid}]'
        for k in ('w', 'role', 'gloss'):
            if not t.get(k):
                errors.append(f'{where}: missing `{k}`')
        if t.get('role') and t['role'] not in roles:
            errors.append(f"{where}: role '{t['role']}' not in LANG_ROLES {sorted(roles)}")
        if not t.get('src'):
            warnings.append(f'{where} ({t.get("w","?")}): 未溯源 — no `src`')

    # ── passage order ──
    if sorted(order) != sorted(passages):
        only_order = set(order) - set(passages)
        only_files = set(passages) - set(order)
        if only_order:
            errors.append(f'_order.json lists missing passages: {sorted(only_order)}')
        if only_files:
            errors.append(f'content/ has passages absent from _order.json: {sorted(only_files)}')
    if len(order) != len(set(order)):
        errors.append('_order.json has duplicate ids')

    # ── passages: structure + every marker / ref resolves ──
    for pid, p in passages.items():
        where = f'passage[{pid}]'
        if p.get('id') != pid:
            errors.append(f"{where}: file id '{pid}' != record id '{p.get('id')}'")
        for k in ('id', 'title', 'lines'):
            if not p.get(k):
                errors.append(f'{where}: missing `{k}`')
        for line in p.get('lines', []):
            for tok in MARK_ENT.findall(line):
                if _id(tok) not in ents:
                    errors.append(f'{where}: «{tok}» → unknown entity id `{_id(tok)}`')
            for tok in MARK_LNG.findall(line):
                if _id(tok) not in lang:
                    errors.append(f'{where}: ⟨{tok}⟩ → unknown lang id `{_id(tok)}`')

        m = p.get('map')
        if m:
            pt_ids = set()
            for pt in m.get('points', []):
                pt_ids.add(pt.get('id'))
                ll = pt.get('ll')
                if not (isinstance(ll, list) and len(ll) == 2 and all(isinstance(v, (int, float)) for v in ll)):
                    errors.append(f"{where}.map point '{pt.get('id')}': ll must be [lng,lat] numbers, got {ll!r}")
                elif not (LNG[0] <= ll[0] <= LNG[1] and LAT[0] <= ll[1] <= LAT[1]):
                    warnings.append(f"{where}.map point '{pt.get('id')}': ll {ll} outside China bbox — check lng/lat order")
                if pt.get('ref') and pt['ref'] not in ents:
                    errors.append(f"{where}.map point '{pt.get('id')}': ref '{pt['ref']}' not an entity")
            for rid in m.get('route', []):
                if rid not in pt_ids:
                    errors.append(f"{where}.map.route id '{rid}' not among points")

        rel = p.get('rel')
        if rel:
            for n in rel.get('nodes', []):
                if n.get('id') and n['id'] not in ents:
                    warnings.append(f"{where}.rel node '{n.get('id')}' not an entity (ok if intentional)")

        for r in p.get('rise', []):
            if r.get('ref') and r['ref'] not in ents:
                warnings.append(f"{where}.rise '{r.get('title')}': ref '{r['ref']}' not an entity")

    return errors, warnings


def main():
    data = load()
    errors, warnings = check(data)
    for w in warnings:
        print('  ⚠ ', w)
    for e in errors:
        print('  ✗ ', e)
    print(f'\nvalidate: {len(errors)} error(s), {len(warnings)} warning(s) '
          f'({len(data["entities"])} entities, {len(data["lang"])} lang, {len(data["passages"])} passages)')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
