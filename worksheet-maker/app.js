/* Worksheet Maker — runs the zhongwen-worksheets Python generator entirely
 * client-side via Pyodide. No server, no build step: this file, index.html,
 * py/ (a copy of zhw/) and data/ (book*.json + timing.json) are the whole app.
 */
"use strict";

const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.29.4/full/";

const ZHW_FILES = [
  "zhw/__init__.py", "zhw/model.py", "zhw/ingest.py", "zhw/enrich.py",
  "zhw/render.py", "zhw/validate.py", "zhw/build.py", "zhw/webapi.py",
  "zhw/qbank/__init__.py", "zhw/qbank/form.py", "zhw/qbank/sound.py",
  "zhw/qbank/meaning.py", "zhw/qbank/sentence.py", "zhw/qbank/reading.py",
  "zhw/qbank/puzzle.py", "zhw/qbank/drill.py",
];
const DATA_FILES = ["book7.json", "book8.json", "book9.json", "timing.json"];
const DATA_PATHS = ["data/book9.json", "data/book7.json", "data/book8.json"];

const $ = (id) => document.getElementById(id);
const bootStatus = $("boot-status");
const generateBtn = $("generate-btn");
const errorBox = $("error-box");

let pyodide = null;
let webapi = null;
let lessonsByBook = {};   // { bookNumber: [{lesson, title}, ...] }
let lastHtml = "";

function setStatus(text, spinning = true) {
  bootStatus.innerHTML = (spinning ? '<span class="spinner"></span> ' : "") + text;
}

function showError(msg) {
  errorBox.style.display = "block";
  errorBox.textContent = msg;
}
function clearError() {
  errorBox.style.display = "none";
  errorBox.textContent = "";
}

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}: ${res.status}`);
  return res.text();
}

async function installFiles(paths, baseUrl, baseFsDir) {
  const dirs = new Set(paths.map((p) => {
    const parts = (baseFsDir + "/" + p).split("/");
    parts.pop();
    return parts.join("/");
  }));
  for (const d of dirs) {
    try { pyodide.FS.mkdirTree(d); } catch (e) { /* already exists */ }
  }
  await Promise.all(paths.map(async (p) => {
    const text = await fetchText(baseUrl + p);
    pyodide.FS.writeFile(baseFsDir + "/" + p, text, { encoding: "utf8" });
  }));
}

async function boot() {
  try {
    setStatus("Loading Python runtime…");
    pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

    setStatus("Installing pinyin support…");
    try {
      await pyodide.loadPackage("micropip");
      const micropip = pyodide.pyimport("micropip");
      await micropip.install("pypinyin");
    } catch (e) {
      console.warn("pypinyin unavailable — auto-pinyin fallback will be blank where the textbook doesn't supply it.", e);
    }

    setStatus("Loading worksheet generator…");
    await installFiles(ZHW_FILES, "py/", "");
    await installFiles(DATA_FILES, "data/", "/data");

    pyodide.runPython("import sys, os\nos.chdir('/')\nif '' not in sys.path: sys.path.insert(0, '')");
    webapi = pyodide.pyimport("zhw.webapi");

    setStatus("Reading lesson data…");
    const raw = JSON.parse(webapi.list_lessons(JSON.stringify(DATA_PATHS)));
    if (raw.error) throw new Error(raw.error);
    for (const b of raw.books) lessonsByBook[b.book] = b;

    populateBookSelect(raw.books);
    $("book-select").disabled = false;
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate worksheet";
    setStatus("Ready", false);
  } catch (e) {
    console.error(e);
    setStatus("Failed to load — see console", false);
    showError("Couldn't start the in-browser Python runtime: " + e.message +
      "\n\nCheck your internet connection (this loads Pyodide from a CDN on first visit) and reload.");
  }
}

function populateBookSelect(books) {
  const sel = $("book-select");
  sel.innerHTML = "";
  for (const b of books) {
    const opt = document.createElement("option");
    opt.value = b.book;
    opt.textContent = `${b.label} (Book ${b.book})`;
    sel.appendChild(opt);
  }
  sel.value = books[books.length - 1].book;   // default to the most advanced book
  onBookChange();
}

function onBookChange() {
  const book = parseInt($("book-select").value, 10);
  renderLessonChecks(book);
  renderReviewBookChecks(book);
}

function renderLessonChecks(book) {
  const wrap = $("lesson-checks");
  wrap.innerHTML = "";
  const lessons = lessonsByBook[book].lessons;
  lessons.forEach((l, i) => {
    const label = document.createElement("label");
    label.className = "chk";
    label.innerHTML = `<input type="checkbox" value="${l.lesson}" ${i === 0 ? "checked" : ""}/> ${l.lesson}. ${l.title || ""}`;
    wrap.appendChild(label);
  });
}

function renderReviewBookChecks(currentBook) {
  const wrap = $("review-book-checks");
  wrap.innerHTML = "";
  const others = Object.keys(lessonsByBook).map(Number).filter((b) => b !== currentBook);
  others.sort((a, b) => a - b);
  for (const b of others) {
    const label = document.createElement("label");
    label.className = "chk";
    label.innerHTML = `<input type="checkbox" value="${b}" ${b < currentBook ? "checked" : ""}/> ${lessonsByBook[b].label} (Book ${b})`;
    wrap.appendChild(label);
  }
}

function buildOptions() {
  const book = parseInt($("book-select").value, 10);
  const lessons = [...document.querySelectorAll("#lesson-checks input:checked")]
    .map((c) => parseInt(c.value, 10));
  const reviewBooks = $("review-toggle").checked
    ? [...document.querySelectorAll("#review-book-checks input:checked")].map((c) => parseInt(c.value, 10))
    : [];
  const review = reviewBooks.length
    ? { books: reviewBooks, ratio: parseInt($("review-ratio").value, 10) / 100, tier: "write" }
    : null;
  const allow = ["verified", "authored", "open"];
  if ($("derived-toggle").checked) allow.push("derived");
  const minutes = parseFloat($("minutes-input").value);
  return {
    data_paths: DATA_PATHS,
    book, lessons,
    vocabulary: $("vocab-select").value,
    review,
    seed: parseInt($("seed-input").value, 10) || Math.floor(Math.random() * 1e8),
    minutes: Number.isFinite(minutes) && minutes > 0 ? minutes : null,
    allow,
    style: $("style-select").value,
    density: $("density-select").value,
    lang: $("lang-select").value,
    show_key: true,
  };
}

function renderReport(rep) {
  const bits = [
    `<b>${rep.questions}</b> questions`, `<b>${rep.items}</b> items`,
    `≈<b>${rep.minutes}</b> min`, `≈<b>${rep.est_pages}</b> pages`,
  ];
  if (rep.review) bits.push(`<b>${rep.review.count}</b> review chars`);
  $("report-line").innerHTML = bits.join(" · ");

  const diagParts = [];
  if (rep.shortfall) diagParts.push(`⚠ ${rep.shortfall}`);
  if (rep.page_warning) diagParts.push(rep.page_warning);
  if (rep.skipped && rep.skipped.length) diagParts.push("Skipped: " + rep.skipped.join(" · "));
  if (rep.leaks && Object.keys(rep.leaks).length) diagParts.push("⚠ Vocabulary leak: " + JSON.stringify(rep.leaks));
  let diag = document.getElementById("diag");
  if (diagParts.length) {
    if (!diag) {
      diag = document.createElement("details");
      diag.id = "diag";
      diag.innerHTML = '<summary>Build notes</summary><div class="diag-body"></div>';
      $("preview-bar").after(diag);
    }
    diag.style.display = "";
    diag.querySelector(".diag-body").innerHTML = diagParts.map((p) => `<div>${p}</div>`).join("");
  } else if (diag) {
    diag.style.display = "none";
  }
}

async function onGenerate() {
  clearError();
  const lessons = [...document.querySelectorAll("#lesson-checks input:checked")];
  if (!lessons.length) {
    showError("Pick at least one lesson.");
    return;
  }
  generateBtn.disabled = true;
  generateBtn.textContent = "Generating…";
  try {
    const opts = buildOptions();
    const result = JSON.parse(webapi.generate_worksheet(JSON.stringify(opts)));
    if (result.error) {
      showError(result.error);
    } else {
      lastHtml = result.html;
      $("preview-frame").srcdoc = result.html;
      $("preview-frame").style.display = "";
      $("empty-state").style.display = "none";
      $("preview-bar").style.display = "flex";
      $("download-btn").disabled = false;
      $("print-btn").disabled = false;
      renderReport(result.report);
    }
  } catch (e) {
    console.error(e);
    showError("Generation failed: " + e.message);
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate worksheet";
  }
}

function wireUp() {
  $("book-select").addEventListener("change", onBookChange);
  $("review-toggle").addEventListener("change", (e) => {
    $("review-block").toggleAttribute("data-off", !e.target.checked);
  });
  $("review-ratio").addEventListener("input", (e) => {
    $("ratio-val").textContent = e.target.value + "%";
  });
  generateBtn.addEventListener("click", onGenerate);
  $("print-btn").addEventListener("click", () => $("preview-frame").contentWindow.print());
  $("download-btn").addEventListener("click", () => {
    const blob = new Blob([lastHtml], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "worksheet.html";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}

wireUp();
boot();
