"""Layout regression checks. Run: python -m tests.test_layout <sheet.html>"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from zhw.render import CSS

def check(path):
    h = pathlib.Path(path).read_text(encoding="utf-8")
    sheet = h.split('<div class="sheet key"', 1)[0]
    defined = set(re.findall(r'\.([a-zA-Z][\w-]*)', CSS))
    used = set()
    for attr in re.findall(r'class="([^"]+)"', h):
        used.update(attr.split())
    fails = []

    ghost = sorted(c for c in used - defined
                   if c not in {"sheet", "key", "en", "zh"} and not c.startswith("c"))
    if ghost:
        fails.append(f"class used but not styled (invisible element): {ghost}")

    # a bracket and a rule together is two cues for one answer
    if re.search(r'（\s*<span class="blank', sheet):
        fails.append("bracket wrapped around a ruled blank — pick one affordance")
    if re.search(r'class="brk"[^>]*>[^<]*（', sheet):
        fails.append("literal （ text next to a .brk element — double bracket")
    # a circle instruction with a fill-in bracket is the same double-cue problem
    if "圈出" in sheet or "circle" in sheet.lower():
        near_brk = re.search(r'圈出.{0,400}?class="brk"', sheet, re.S)
        if near_brk:
            fails.append("instruction says to circle, but a fill-in bracket is "
                         "also present in the same question")

    # nothing on a classroom sheet may read as a score
    for pat, name in [(r'得分', "score field"), (r'×\s*\d+\s*=', "mark tally"),
                      (r'\d+\s*分(?!钟)', "marks"), (r'\d+\s*题', "question count"),
                      (r'分钟', "time limit")]:
        if re.search(pat, sheet):
            fails.append(f"student sheet shows a {name}")

    for f in fails:
        print("FAIL ", f)
    if not fails:
        print(f"PASS  {pathlib.Path(path).name}: no ghost classes, single blank "
              f"affordance, nothing score-like")
    return not fails

if __name__ == "__main__":
    args = sys.argv[1:] or ["out/b3l1-2-3-4-45min.html"]
    sys.exit(0 if all(check(a) for a in args) else 1)
