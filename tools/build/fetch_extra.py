#!/usr/bin/env python3
"""Fetch stroke data + metadata for the ZW1 pilot's 45 missing chars and
MERGE them into learn/library-chars.js (idempotent)."""
import json, re, ssl, urllib.request, urllib.parse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0,'tools/build')
from zw1_extra import ZW1_ADD

CTX=ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
CDN="https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/"
DICT={}
for line in open('tools/build/dictionary.txt',encoding='utf-8'):
    line=line.strip()
    if line: o=json.loads(line); DICT[o['character']]=o
def short_en(d):
    if not d: return ""
    s=re.sub(r'\s+',' ',d.split(';')[0].strip())
    return s[:42].rsplit(' ',1)[0]+'…' if len(s)>42 else s
def fetch(ch):
    url=CDN+urllib.parse.quote(ch)+".json"
    for _ in range(4):
        try: return json.loads(urllib.request.urlopen(url,context=CTX,timeout=25).read())
        except Exception as e: last=e
    raise last

# load current library-chars
txt=open('learn/library-chars.js',encoding='utf-8').read()
head=txt[:txt.index('window.LIBRARY_CHARS = ')]
body=txt[txt.index('= ')+2:].rstrip().rstrip(';')
data=json.loads(body); have={c['ch'] for c in data['chars']}
allc=[c for v in ZW1_ADD.values() for c in v]
todo=[c for c in dict.fromkeys(allc) if c not in have]
print("fetching",len(todo))
def work(ch):
    g=fetch(ch); m=DICT.get(ch,{})
    return {"ch":ch,"py":(m.get('pinyin') or [""])[0],"en":short_en(m.get('definition','')),
            "strokes":len(g['strokes']),"radical":m.get('radical',''),"s":g['strokes'],"m":g['medians']}
new=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(work,c):c for c in todo}
    for f in as_completed(futs):
        new.append(f.result())
# keep order: existing then new in curriculum order
order={c:i for i,c in enumerate(todo)}
new.sort(key=lambda r:order[r['ch']])
data['chars'].extend(new)
open('learn/library-chars.js','w',encoding='utf-8').write(
    head+"window.LIBRARY_CHARS = "+json.dumps(data,ensure_ascii=False)+";\n")
print("merged. total chars now",len(data['chars']))
