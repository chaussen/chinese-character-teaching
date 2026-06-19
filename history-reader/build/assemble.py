#!/usr/bin/env python3
"""Assemble the 史案 data cache into history-reader/data.js (the keystone build).

  registry/meta.json      CATS + LANG_ROLES (presentation config)
  registry/entities.json  global entity registry — the CACHE (dedupes across texts)
  registry/lang.json      language-token registry — per-context glosses
  content/<id>.json       one passage each (lines + map/rel/rise)
  content/_order.json     deterministic passage order
        │
        ▼  validate (refuse build on any ERROR)  →  emit data.js

data.js is GENERATED. Edit the cache/content, then run this — never hand-edit data.js.

Usage:  python3 build/assemble.py        (writes data.js)
        python3 build/assemble.py --check (round-trip check: data.js unchanged → exit 0)
"""
import json, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate  # noqa: E402

OUT = HERE.parent / 'data.js'

HEADER = '''/* 史案 — 史书知识图谱阅读器 · data layer (window.SHI_DATA)
 *
 * ⚠ GENERATED FILE — do not hand-edit. Source of truth is build/:
 *     registry/{meta,entities,lang}.json + content/<id>.json
 *   Edit those, then run:  python3 build/assemble.py
 *
 * Two principles are baked into the structure on purpose:
 *
 *   1. Sourced data is the product. Every ENTITIES record carries provenance
 *      (`src`) and cross-references (`seen`). The UI marks any entity WITHOUT a
 *      `src` as 未溯源 rather than silently presenting it as fact.
 *
 *   2. One passage today, the whole canon tomorrow. ENTITIES is a *global
 *      registry* keyed by canonical id; PASSAGES is a collection whose lines
 *      reference the registry by id («entityId» knowledge · ⟨langId⟩ language).
 *      A marker may carry a surface override — «id|高祖» / ⟨id|surface⟩ — so one
 *      canonical entity can appear under different names across texts while
 *      still resolving to the same id (its `seen` aggregates every text).
 */
(function () {
'''

FOOTER = '''
  window.SHI_DATA = { CATS, LANG_ROLES, ENTITIES, LANG, PASSAGES };
})();
'''


def js_const(name, obj, indent=2):
    """`const NAME = <json>;` — JSON is valid JS; re-indent to sit inside the IIFE."""
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    body = '\n'.join((' ' * indent + ln if ln else ln) for ln in body.split('\n')).lstrip()
    return f'{" " * indent}const {name} = {body};\n'


def _strip_helpers(p):
    # `_`-prefixed keys are ingest scaffolding (_todo / _residue notes); never ship them.
    return {k: v for k, v in p.items() if not k.startswith('_')}


def render(data):
    passages = [_strip_helpers(data['passages'][pid]) for pid in data['order']]
    parts = [HEADER,
             js_const('CATS', data['meta']['CATS']), '\n',
             js_const('LANG_ROLES', data['meta']['LANG_ROLES']), '\n',
             js_const('ENTITIES', data['entities']), '\n',
             js_const('LANG', data['lang']), '\n',
             js_const('PASSAGES', passages),
             FOOTER]
    return ''.join(parts)


def main():
    data = validate.load()
    errors, warnings = validate.check(data)
    for w in warnings:
        print('  ⚠ ', w)
    if errors:
        for e in errors:
            print('  ✗ ', e)
        print(f'\nassemble: REFUSED — {len(errors)} error(s). Fix the cache/content first.')
        sys.exit(1)

    js = render(data)

    if '--check' in sys.argv:
        cur = OUT.read_text(encoding='utf-8') if OUT.exists() else ''
        if cur != js:
            print('assemble --check: data.js is OUT OF DATE (run assemble.py to regenerate).')
            sys.exit(1)
        print('assemble --check: data.js is up to date.')
        return

    OUT.write_text(js, encoding='utf-8')
    print(f'assemble: wrote {OUT.relative_to(HERE.parent.parent)} — '
          f'{len(data["entities"])} entities, {len(data["lang"])} lang, '
          f'{len(data["passages"])} passages, {len(warnings)} warning(s).')


if __name__ == '__main__':
    main()
