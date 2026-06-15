import json, re, os
ROOT='.'
# load library chars (the 639 new ones needing content)
txt=open('learn/library-chars.js',encoding='utf-8').read()
body=txt[txt.index('= ')+2:].rstrip().rstrip(';')
chars=json.loads(body)['chars']
# dictionary for decomposition + etymology hint
DICT={}
for line in open('tools/build/dictionary.txt',encoding='utf-8'):
    line=line.strip()
    if line:
        o=json.loads(line); DICT[o['character']]=o
# which already have content-extra? skip those (idempotent / don't clobber pilot)
ce=open('learn/content-extra.js',encoding='utf-8').read()
existing=set(re.findall(r'"(.)":\{', ce))

items=[]
for c in chars:
    ch=c['ch']
    if ch in existing: continue
    m=DICT.get(ch,{})
    ety=m.get('etymology') or {}
    items.append({
        "ch":ch,"py":c['py'],"en":c['en'],"radical":c['radical'],
        "decomp":m.get('decomposition',''),
        "hint":ety.get('hint',''),"etype":ety.get('type',''),
    })
print("need content for",len(items),"chars")
os.makedirs('tools/build/content',exist_ok=True)
B=40
batches=[items[i:i+B] for i in range(0,len(items),B)]
for i,b in enumerate(batches,1):
    json.dump(b, open(f'tools/build/content/in_{i:02d}.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print("wrote",len(batches),"batch input files of <=",B)
