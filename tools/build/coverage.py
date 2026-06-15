import re, sys
sys.path.insert(0, 'tools/build')
from curriculum import GRADES

def chars_in(path):
    txt = open(path, encoding='utf-8').read()
    return set(re.findall(r'"ch"\s*:\s*"(.)"', txt))

have = set()
for p in ['learn/app-data.js','learn/general-data.js','learn/char-data.js']:
    try: have |= chars_in(p)
    except FileNotFoundError: pass
print("existing stroke chars:", len(have))

allc=[]
for lines in GRADES.values():
    for l in lines: allc+=list(l)
uniq=sorted(set(allc))
missing=[c for c in uniq if c not in have]
present=[c for c in uniq if c in have]
print(f"curriculum unique {len(uniq)}: present {len(present)}, MISSING {len(missing)}")
open('tools/build/missing.txt','w',encoding='utf-8').write(''.join(missing))
print("missing sample:", ''.join(missing[:60]))
