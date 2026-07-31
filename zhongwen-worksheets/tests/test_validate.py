"""Proof that the ambiguity checks actually fire. Run: python -m tests.test_validate"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from zhw.render import Question
from zhw.validate import validate

def q(**kw):
    d = dict(type_id="x", title_zh="", title_en="", answer_mode="bijection")
    d.update(kw); return Question(**d)

CASES = [
 ("instruction promises an example ('照例子') that is not shown",
  q(type_id="minimal_pairs", answer_mode="open",
    instruction_zh="照例子比一比，再组词语。", body_html="<div>no example here</div>"),
  "unfulfilled-claim"),
 ("连线 with two chars sharing a reading",
  q(type_id="pinyin_match", solution=[("妈","mā"),("抹","mā"),("书","shū")]),
  "ambiguous-link"),
 ("汉英连线 with a gloss nested in another",
  q(type_id="gloss_match", solution=[("大树","tree"),("树木","big tree")]),
  "overlapping-answer"),
 ("单选 where a distractor is also correct",
  q(type_id="lookalike", solution=[("（ ）弟","弟")], distractors=["弟"], answer_mode="unique"),
  "distractor-is-answer"),
 ("a type that declares no machine-checkable key",
  q(type_id="anything", answer_mode="teacher"),
  "needs-human-judgement"),
 ("选词填空 where a bank word already sits in the sentence",
  q(type_id="cloze", answer_mode="unique", solution=[("我去＿＿。","学校")],
    meta={"gaps":[("我去学校。","学校")], "bank":["学校","公园","我"]}),
  "bank-word-in-sentence"),
 ("字词搜索 where padding re-spells a target",
  q(type_id="word_search", answer_mode="bijection", solution=[("公园","A1")],
    meta={"grid":[list("公园大"),list("树公园"),list("花草木")], "targets":["公园"]}),
  "duplicate-in-grid"),
 ("排列句序 built from an unordered example list",
  q(type_id="sentence_order", answer_mode="bijection",
    solution=[("我去公园。","1"),("花很小。","2")], meta={"from_passage": False}),
  "no-canonical-order"),
 ("量词 bank whose key does not match the bank",
  q(type_id="measure_word", solution=[("树","棵"),("花","朵")], meta={"bank":["棵","个"]}),
  "bank-mismatch"),
]

if __name__ == "__main__":
    fails = 0
    for name, question, expect in CASES:
        kinds = [i.kind for i in validate(question, None)]
        ok = expect in kinds
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}\n      caught: {kinds or 'nothing'}")
    print(f"\n{len(CASES)-fails}/{len(CASES)} ambiguity traps caught")

    # Registry labels (shown in --audit) must match what actually prints on a
    # sheet — otherwise the audit becomes a document that quietly lies about
    # what the tool does. This would have caught the use_the_word drift.
    import random
    from zhw.model import Corpus, Scope
    from zhw import enrich
    from zhw.qbank import REGISTRY, Ctx
    c = Corpus.load("data/zhongwen.json")
    enrich.enrich_corpus(c)
    sc = Scope.build(c, 3, [1, 2, 3, 4])
    drift = []
    for tid, spec in REGISTRY.items():
        try:
            gen = spec.fn(Ctx(scope=sc, rng=random.Random("drift"),
                              count=spec.default_count))
        except Exception:
            continue
        if gen and gen.title_zh != spec.name_zh:
            drift.append(f"{tid}: registry says {spec.name_zh!r}, "
                         f"actual output says {gen.title_zh!r}")
    if drift:
        print(f"\nFAIL  {len(drift)} type(s) have a stale registry label:")
        for d in drift:
            print("     ", d)
        fails += len(drift)
    else:
        print(f"\nPASS  all {len(REGISTRY)} registry labels match their actual output")

    sys.exit(1 if fails else 0)
