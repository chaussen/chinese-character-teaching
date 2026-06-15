import json, re, sys
global_window={}
# build CHAR_INDEX metadata from all sources
def load(path):
    txt=open(path,encoding='utf-8').read()
    body=txt[txt.index('= ')+2:].rstrip().rstrip(';') if '= ' in txt else None
    return txt
import importlib.util
# get CHAR_INDEX via node? simpler: parse via regex for ch/py/en/radical
def chars_meta(path):
    txt=open(path,encoding='utf-8').read()
    out={}
    for m in re.finditer(r'\{"ch":"(.)","py":"([^"]*)","en":"([^"]*)","strokes":\d+,"radical":"([^"]*)"', txt):
        ch=m.group(1)
        out.setdefault(ch, dict(ch=ch,py=m.group(2),en=m.group(3),radical=m.group(4)))
    # app-data has different key order: ch,py,en,strokes,radical
    for m in re.finditer(r'\{"ch":"(.)","py":"([^"]*)","en":"([^"]*)","strokes":\d+,"radical":"([^"]*)"', txt):
        pass
    return out
meta={}
for p in ['learn/library-chars.js','learn/general-data.js','learn/app-data.js']:
    for ch,d in chars_meta(p).items():
        meta.setdefault(ch,d)
# dictionary for decomp/hint
DICT={}
for line in open('tools/build/dictionary.txt',encoding='utf-8'):
    line=line.strip()
    if line:
        o=json.loads(line);DICT[o['character']]=o

# the 115 list from validation: chars in lessons, in index, no content
sys.path.insert(0,'tools/build'); from curriculum import GRADES
ce=open('learn/content-extra.js',encoding='utf-8').read()
have=set(re.findall(r'"(.)":\s*\{', ce))
lesson=[]
for lines in GRADES.values():
    for l in lines: lesson+=list(l)
need=[c for c in dict.fromkeys(lesson) if c not in have]
print("lesson chars without content:",len(need))
items=[]
nometa=[]
for ch in need:
    m=meta.get(ch)
    if not m: nometa.append(ch); 
    dm=DICT.get(ch,{}); ety=dm.get('etymology') or {}
    m=m or {}
    py=m.get('py') or (dm.get('pinyin') or [''])[0]
    en=m.get('en') or (dm.get('definition','').split(';')[0].strip())
    rad=m.get('radical') or dm.get('radical','')
    items.append({"ch":ch,"py":py,"en":en,"radical":rad,"decomp":dm.get('decomposition',''),
                  "hint":ety.get('hint',''),"etype":ety.get('type','')})
print("no meta found for:",''.join(nometa) or 'none')
import os
os.makedirs('tools/build/content2',exist_ok=True)
B=40
for i in range(0,len(items),B):
    json.dump(items[i:i+B],open(f'tools/build/content2/in_{i//B+1:02d}.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print("wrote",(len(items)+B-1)//B,"batch files")
