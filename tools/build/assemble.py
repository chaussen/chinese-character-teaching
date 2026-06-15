import json, re, glob, sys
from pypinyin import pinyin, Style

# IDC (decomposition lead char) -> struct shape used by the 结构 builder
IDC = {"⿰":"lr","⿱":"tb","⿲":"lmr","⿳":"tmb","⿴":"full",
       "⿵":"sw","⿶":"sw","⿷":"sw","⿸":"sw","⿹":"sw","⿺":"sw","⿻":"single"}
def struct_of(decomp):
    if not decomp: return "single"
    c=decomp[0]
    return IDC.get(c,"single")

# load dictionary decomps for struct
DICT={}
for line in open('tools/build/dictionary.txt',encoding='utf-8'):
    line=line.strip()
    if line:
        o=json.loads(line); DICT[o['character']]=o

def py_tone(text):
    return [s[0] for s in pinyin(text, style=Style.TONE, errors=lambda x:[''])]

PUNCT=set("。，！？、；：“”‘’（）《》—…·,.!?\"'()")

def build_seg(cn):
    out=[]
    # per-character pinyin in context (phrase-aware)
    plist = py_tone(cn)
    for i,ch in enumerate(cn):
        if ch in PUNCT or not ('一'<=ch<='鿿'):
            out.append([ch,""])
        else:
            p = plist[i] if i < len(plist) else ""
            out.append([ch, p])
    return out

merged={}
errors=[]
for f in sorted(glob.glob('tools/build/content/out_*.json')+glob.glob('tools/build/content2/out_*.json')+glob.glob('tools/build/content3/out_*.json')):
    data=json.load(open(f,encoding='utf-8'))
    for ch,v in data.items():
        if len(ch)!=1: errors.append((f,ch,"bad key")); continue
        w=(v.get('word') or {})
        wv=w.get('w','')
        sent=(v.get('sentence') or {})
        cn=sent.get('cn','')
        if ch not in wv: errors.append((f,ch,f"word '{wv}' lacks char")); 
        if ch not in cn: errors.append((f,ch,f"sentence '{cn}' lacks char"))
        entry={"struct":struct_of(DICT.get(ch,{}).get('decomposition',''))}
        if v.get('origin'): entry['origin']=v['origin'].strip()
        if wv:
            wpy=" ".join(py_tone(wv))
            entry['word']={"w":wv,"py":wpy,"en":w.get('en','').strip()}
        if cn:
            entry['sentence']={"seg":build_seg(cn),"en":sent.get('en','').strip()}
        merged[ch]=entry

print("assembled",len(merged),"entries; errors:",len(errors))
for e in errors[:30]: print("  ERR",e)

# merge into existing CONTENT_EXTRA (preserve pilot entries, new ones added)
ce=open('learn/content-extra.js',encoding='utf-8').read()
body=ce[ce.index('window.CONTENT_EXTRA = ')+len('window.CONTENT_EXTRA = '):].rstrip().rstrip(';')
existing=json.loads(body)
print("existing pilot entries:",len(existing))
added=0
for ch,e in merged.items():
    existing[ch]=e; added+=1
print("added",added,"new entries; total now",len(existing))

HEADER=ce[:ce.index('window.CONTENT_EXTRA')]
open('learn/content-extra.js','w',encoding='utf-8').write(
    HEADER+"window.CONTENT_EXTRA = "+json.dumps(existing,ensure_ascii=False)+";\n")
print("written learn/content-extra.js")
