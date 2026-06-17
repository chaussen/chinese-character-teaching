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
    # Compute pinyin per maximal run of Han characters. Doing it run-by-run keeps
    # phrase context (tone sandhi / heteronyms) while staying perfectly aligned —
    # pypinyin collapses *consecutive* non-Han chars (e.g. 》，) into one token, so
    # a single positional list over the whole string would drift after them.
    out=[]
    i,n=0,len(cn)
    while i<n:
        if '一'<=cn[i]<='鿿':
            j=i
            while j<n and '一'<=cn[j]<='鿿': j+=1
            plist=py_tone(cn[i:j])
            for k,ch in enumerate(cn[i:j]):
                out.append([ch, plist[k] if k<len(plist) else ""])
            i=j
        else:
            out.append([cn[i],""])
            i+=1
    return out

merged={}
errors=[]
for f in sorted(glob.glob('tools/build/content*/out_*.json')):
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
            sobj={"seg":build_seg(cn),"en":sent.get('en','').strip()}
            if sent.get('src'): sobj['src']=sent['src'].strip()
            entry['sentence']=sobj
        merged[ch]=entry

print("assembled",len(merged),"entries; errors:",len(errors))
for e in errors[:30]: print("  ERR",e)

# merge into existing CONTENT_EXTRA (preserve pilot entries, new ones added)
ce=open('learn/content-extra.js',encoding='utf-8').read()
body=ce[ce.index('window.CONTENT_EXTRA = ')+len('window.CONTENT_EXTRA = '):].rstrip().rstrip(';')
existing=json.loads(body)
print("existing pilot entries:",len(existing))
added=0; updated=0
for ch,e in merged.items():
    if ch in existing:
        # merge field-by-field so a partial out_* (e.g. only a sentence) never
        # clobbers fields the existing entry already carries.
        cur=existing[ch]
        for k,val in e.items():
            if k=="struct" and cur.get("struct") and not DICT.get(ch,{}).get('decomposition'):
                continue  # keep a previously-known struct over a "single" guess
            cur[k]=val
        updated+=1
    else:
        existing[ch]=e; added+=1
print("added",added,"new entries; updated",updated,"; total now",len(existing))

HEADER=ce[:ce.index('window.CONTENT_EXTRA')]
open('learn/content-extra.js','w',encoding='utf-8').write(
    HEADER+"window.CONTENT_EXTRA = "+json.dumps(existing,ensure_ascii=False)+";\n")
print("written learn/content-extra.js")
