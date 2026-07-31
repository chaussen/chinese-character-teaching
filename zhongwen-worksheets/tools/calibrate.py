"""Re-fit the page estimator against real Chromium renders.
Needs: pip install playwright pymupdf && python -m playwright install chromium
"""
import subprocess, json, pathlib, statistics, sys
from playwright.sync_api import sync_playwright
import fitz

CASES = [("classroom","drill",""),("standard","workbook",""),
         ("full","workbook",""),("quick","workbook",""),("revision","drill","")]

def run(book=3, lessons=(1,2,3,4)):
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for preset, style, dens in CASES:
            a = ["python3","-m","zhw.build","--book",str(book)]
            for l in lessons: a += ["--lesson", str(l)]
            a += ["--preset",preset,"--style",style,"--no-key","--out","/tmp/cal"]
            if dens: a += ["--density",dens]
            out = json.loads(subprocess.run(a,capture_output=True,text=True).stdout)[0]
            pg = b.new_page(); pg.goto("file://"+str(pathlib.Path(out["file"]).resolve()))
            pg.wait_for_timeout(500); pg.pdf(path="/tmp/x.pdf",format="A4",print_background=True)
            pg.close()
            rows.append((preset, out["est_pages"], fitz.open("/tmp/x.pdf").page_count))
        b.close()
    for r in rows: print(f"{r[0]:16} est {r[1]:>6}  actual {r[2]}")
    print("mean ratio:", round(statistics.mean(a/e for _,e,a in rows if e), 3))

if __name__ == "__main__":
    run()
