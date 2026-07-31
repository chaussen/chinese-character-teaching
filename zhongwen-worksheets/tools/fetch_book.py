"""
Auto-fetch and parse 《中文》(修订版) lesson data for any book, from the
official per-lesson teaching-reference PDFs on 中国华文教育网.

    python3 tools/fetch_book.py --book 7
    python3 tools/fetch_book.py --book 8 --lessons 1,2,3
    python3 tools/fetch_book.py --book 6 --pinyin      # fill write-char pinyin via pypinyin

What this DOES fully automate (text-based PDFs, no OCR needed):
  - lesson title
  - 生字 write-character list, with radical + stroke count + traditional form,
    cross-checked against the lesson's own stated "会读会写本课的N个生字"
  - 认读 read-only character list
  - the 2 "重点学习的句子" key sentences per lesson (verbatim, textbook-exact)

What this CANNOT get (needs the scanned main-textbook PDF + a vision/manual
pass, same as was done for book 9 -- see the printed reminder at the end):
  - 词语 (vocabulary) with pinyin + English gloss  -- textbook's own
    音序生词表 is in the main textbook's back matter, which is a scanned
    image, not extractable text
  - full 课文 passage text
  - textbook-confirmed pinyin for 认读 (read-only) characters
  - write-char pinyin, UNLESS --pinyin is passed (falls back to pypinyin,
    which is enrichment-quality, not textbook-quality -- flagged as such)

Source URLs (generalize across at least books 1-12):
  teaching ref (text PDF): http://old.hwjyw.com/fj/jcxz/zwjxck/{book}/{lesson}.pdf
  main textbook (scanned): https://www.culture-oushi.com/files/zw{book}.pdf
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zhw.model import CharEntry, Corpus, Lesson, WordEntry  # noqa: E402

TEACHING_REF_URL = "http://old.hwjyw.com/fj/jcxz/zwjxck/{book}/{lesson}.pdf"
MAIN_TEXTBOOK_URL = "https://www.culture-oushi.com/files/zw{book}.pdf"
UA = "Mozilla/5.0"

Q = '[“”"]'  # curly-left, curly-right, or straight quote -- these PDFs mix all three
CHAR_LINE_RE = re.compile(
    r'^[ \t]*([一-鿿])(?:\s*［([^］]+)］)?\s*[^，,。]{0,10}'
    r'(?:结构|独体字|独字体)\s*[，,]\s*'
    rf'(?:部|剖)首是\s*{Q}([^“”"]*){Q}(?:\s*(?:或|、)\s*{Q}[^“”"]*{Q})*\s*[，,]\s*'
    r'(?:共\s*)?(\d+)\s*(?:画)?',
    re.M,
)


def clean(text: str) -> str:
    """Undo font-driven whitespace noise without touching real content."""
    text = text.replace("\x0c", "\n")  # form-feed page breaks -> real line breaks
    text = re.sub(r'(?<=[一-鿿])[ \t]+(?=[一-鿿])', '', text)
    return text


def fetch_pdf(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
    except Exception as e:
        print(f"  ! fetch failed {url}: {e}")
        return False
    if len(data) < 500:  # 404 pages / redirects to an error page are tiny
        print(f"  ! {url} returned suspiciously small response ({len(data)}B), skipping")
        return False
    dest.write_bytes(data)
    return True


def pdf_to_text(pdf_path: Path) -> str:
    out = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                          capture_output=True, text=True)
    return out.stdout


def parse_lesson(text: str, book: int, lesson: int) -> tuple[Lesson, dict]:
    text = clean(text)
    report = {"write_expected": None, "write_found": None, "ok": True, "notes": []}

    first_line = next((l for l in text.splitlines() if l.strip()), "")
    m = re.match(r'^\d+[\.、]\s*(.+)$', first_line.strip())
    title = m.group(1).strip() if m else first_line.strip()

    m = re.search(r'(?:会读会写|学会)本课的\s*(\d+)\s*个生字', text)
    write_count = int(m.group(1)) if m else None
    report["write_expected"] = write_count

    # Boundaries are anchored on known section-keyword text, never on the
    # leading "N. " / "N、" enumeration punctuation in front of them: some
    # scan batches have a font whose period/dunhao glyph maps to a random
    # hanzi (e.g. "3援词语教学" instead of "3. 词语教学"), which breaks any
    # lookahead that requires seeing real ASCII/CJK punctuation there.
    m = re.search(r'会认读下列字[，,][^：:]*[：:]\s*(.*?)'
                  r'(?=掌握本课的词语|学习本课的词语|熟练地背诵|二、)', text, re.S)
    read_chars = re.findall(r'[一-鿿]', m.group(1)) if m else []

    m = re.search(r'重点学习(?:的)?句子[：:](.*?)'
                  r'(?=流利地朗读课文|准确地讲述课文内容|二、)', text, re.S)
    sentences = []
    if m:
        for p in re.split(r'（\d+）', m.group(1))[1:]:
            p = re.sub(r'\s+', '', p)
            if p:
                sentences.append(p)

    m = re.search(r'字形教学(.*?)(?=词语教学|句子教学|课文教学'
                  r'|参考资料|练习答案|四、|$)', text, re.S)
    write_chars = []
    if m:
        for mm in CHAR_LINE_RE.finditer(m.group(1)):
            ch, trad, radical, stroke = mm.groups()
            write_chars.append((ch, trad, radical, int(stroke)))
    report["write_found"] = len(write_chars)

    if write_count is not None and len(write_chars) != write_count:
        report["ok"] = False
        report["notes"].append(
            f"write-char count mismatch: found {len(write_chars)}, textbook says {write_count} "
            f"-- check the 字形教学 section by hand for lesson {lesson}"
        )
    if not sentences:
        report["notes"].append("no key sentences parsed -- check manually")

    ls = Lesson(book=book, lesson=lesson, title=title)
    seen = set()
    for ch, trad, radical, stroke in write_chars:
        if ch in seen:
            continue
        seen.add(ch)
        e = CharEntry(char=ch, tier="write", book=book, lesson=lesson)
        if radical and ord(radical[:1] or " ") < 0xE000:  # skip PUA glyph artifacts
            e.radical = radical.strip()
        e.stroke_count = stroke
        # `trad` (traditional form) is parsed but has no field in CharEntry's
        # current schema, so it's dropped here -- add a `traditional` field
        # to CharEntry if this is worth keeping.
        ls.chars.append(e)
    for ch in read_chars:
        if ch not in seen:
            seen.add(ch)
            ls.chars.append(CharEntry(char=ch, tier="read", book=book, lesson=lesson))
    ls.sentences = sentences
    return ls, report


def fill_pinyin(ls: Lesson) -> None:
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        print("  ! --pinyin requested but pypinyin isn't installed "
              "(pip install -r requirements.txt); leaving pinyin blank")
        return
    for c in ls.chars:
        if not c.pinyin:
            c.pinyin = lazy_pinyin(c.char)[0]
            c.derived.add("pinyin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--lessons", default="1-12",
                     help="e.g. '1-12' or '1,3,5' (default: 1-12)")
    ap.add_argument("--pinyin", action="store_true",
                     help="fill missing write-char pinyin via pypinyin (derived, not textbook-sourced)")
    ap.add_argument("--cache", default=None, help="dir for downloaded PDFs (default: cache/refs/<book>)")
    ap.add_argument("--out", default=None, help="output corpus JSON (default: data/book<N>.json)")
    a = ap.parse_args()

    if "-" in a.lessons:
        lo, hi = a.lessons.split("-")
        lesson_nums = list(range(int(lo), int(hi) + 1))
    else:
        lesson_nums = [int(x) for x in a.lessons.split(",")]

    root = Path(__file__).resolve().parent.parent
    cache = Path(a.cache) if a.cache else root / "cache" / "refs" / str(a.book)
    out_path = Path(a.out) if a.out else root / "data" / f"book{a.book}.json"

    lessons = []
    reports = []
    for lesson in lesson_nums:
        pdf_path = cache / f"{lesson}.pdf"
        url = TEACHING_REF_URL.format(book=a.book, lesson=lesson)
        print(f"lesson {lesson}: {url}")
        if not fetch_pdf(url, pdf_path):
            reports.append((lesson, {"ok": False, "notes": ["download failed"]}))
            continue
        text = pdf_to_text(pdf_path)
        ls, report = parse_lesson(text, a.book, lesson)
        if a.pinyin:
            fill_pinyin(ls)
        lessons.append(ls)
        reports.append((lesson, report))

    corpus = Corpus(lessons, meta={
        "series": "《中文》(修订版) 暨南大学华文学院 / 中国国务院侨务办公室",
        "book": a.book,
        "source": (
            f"Auto-parsed from 中文教学参考第{a.book}册 per-lesson PDFs "
            f"(中国华文教育网, {TEACHING_REF_URL.format(book=a.book, lesson='N')}) "
            "via tools/fetch_book.py. words + passage + read-char pinyin are NOT "
            "populated -- they require the scanned main-textbook back matter "
            f"({MAIN_TEXTBOOK_URL.format(book=a.book)}), which needs a vision/manual "
            "pass same as book 9. See per-lesson notes for any write-char count "
            "mismatches that need a manual check."
        ),
    })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    corpus.save(out_path)

    print(f"\nwrote {out_path}\n")
    print(f"{'lesson':>6}  {'title':<14} {'write':>5}  ok?  notes")
    all_ok = True
    for lesson, report in reports:
        ls = next((l for l in lessons if l.lesson == lesson), None)
        title = ls.title if ls else "(failed)"
        wc = report.get("write_found", "-")
        ok = report.get("ok", False)
        all_ok = all_ok and ok
        notes = "; ".join(report.get("notes", []))
        print(f"{lesson:>6}  {title:<14} {wc!s:>5}  {'OK' if ok else 'CHECK':<5}{notes}")

    print(
        "\nStill needed by hand (or a vision-model pass over "
        f"{MAIN_TEXTBOOK_URL.format(book=a.book)}):\n"
        "  - 词语 vocabulary list with pinyin + gloss (音序生词表, back matter)\n"
        "  - 课文 passage text per lesson\n"
        "  - pinyin for 认读 (read-tier) characters\n"
        + ("" if a.pinyin else "  - pinyin for 生字 write characters (rerun with --pinyin, "
                                "or vision-read the 音序生字表 for textbook-exact readings)\n")
    )
    if not all_ok:
        print("Some lessons need a manual recheck (see CHECK rows above) -- "
              "usually a one-off PDF font/column quirk on a single character.")


if __name__ == "__main__":
    main()
