/* explorer.js — Casey Chinese School · Character Explorer engine
   Pure vanilla, no dependencies. Renders the animated stroke-order "writer",
   the character info, the example sentence, and the wall of characters.
   Stroke data is makemeahanzi 1024 Y-up space (see char-data.js).            */
(function () {
  "use strict";
  var DATA = window.CHAR_DATA || [];
  if (!DATA.length) return;

  var LS = "ccs-charexp";
  var prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- persisted state ----
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(LS)) || {}; } catch (e) {}
  var state = {
    idx: clamp(saved.idx || 0, 0, DATA.length - 1),
    pinyin: saved.pinyin !== false,        // shown by default
    rainbow: !!saved.rainbow,
    numbers: !!saved.numbers,
    speed: saved.speed || 1                // 0.6 slow .. 1.6 fast
  };
  function persist() {
    try { localStorage.setItem(LS, JSON.stringify(state)); } catch (e) {}
  }

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return [].slice.call((r || document).querySelectorAll(s)); }

  // ---- rainbow palette (matches the textbook stroke-cell generator) ----
  function palette(n) {
    var out = [];
    for (var i = 0; i < n; i++) {
      var t = n <= 1 ? 0 : i / (n - 1);
      out.push("hsl(" + (8 + t * 282).toFixed(1) + " 64% 47%)");
    }
    return out;
  }

  // ---- order-number layout (ported from stroke-cell.js) ----
  function layoutNumbers(medians) {
    var orig = medians.map(function (m) { return [m[0][0], 900 - m[0][1]]; });
    var pos = orig.map(function (p) { return [p[0], p[1]]; });
    var R = 104;
    for (var it = 0; it < 90; it++) {
      for (var i = 0; i < pos.length; i++) {
        for (var j = i + 1; j < pos.length; j++) {
          var dx = pos[j][0] - pos[i][0], dy = pos[j][1] - pos[i][1];
          var dist = Math.hypot(dx, dy) || 0.01;
          if (dist < R) {
            var push = (R - dist) / 2; dx /= dist; dy /= dist;
            pos[i][0] -= dx * push; pos[i][1] -= dy * push;
            pos[j][0] += dx * push; pos[j][1] += dy * push;
          }
        }
      }
      for (var k = 0; k < pos.length; k++) {
        pos[k][0] += (orig[k][0] - pos[k][0]) * 0.06;
        pos[k][1] += (orig[k][1] - pos[k][1]) * 0.06;
      }
    }
    pos.forEach(function (p) {
      p[0] = clamp(p[0], 60, 964); p[1] = clamp(p[1], 60, 964);
    });
    return pos;
  }

  function medianPath(m) {
    return "M " + m.map(function (p) { return p[0] + " " + p[1]; }).join(" L ");
  }

  function gridSVG() {
    return '<svg class="writer__grid" viewBox="0 0 1024 1024" aria-hidden="true">' +
      '<rect x="3" y="3" width="1018" height="1018" rx="10" fill="none" class="g-frame"/>' +
      '<line class="g-dash" x1="512" y1="14" x2="512" y2="1010"/>' +
      '<line class="g-dash" x1="14" y1="512" x2="1010" y2="512"/>' +
      '<line class="g-diag" x1="40" y1="40" x2="984" y2="984"/>' +
      '<line class="g-diag" x1="984" y1="40" x2="40" y2="984"/></svg>';
  }

  // ---- build the writer for a character ----
  var writerEl, inkEls = [], seqTimers = [], stepIdx = 0;

  function buildWriter(d) {
    seqTimers.forEach(clearTimeout); seqTimers = [];
    stepIdx = 0;
    var n = d.s.length;
    var cols = state.rainbow ? palette(n) : null;
    var defs = "", ghosts = "", inks = "";
    for (var i = 0; i < n; i++) {
      var col = cols ? cols[i] : "var(--ink-cn)";
      defs += '<clipPath id="cp' + i + '"><path d="' + d.s[i] + '"/></clipPath>';
      ghosts += '<path class="ghost" d="' + d.s[i] + '"/>';
      inks += '<path class="ink" data-i="' + i + '" d="' + medianPath(d.m[i]) +
        '" fill="none" stroke="' + col + '" stroke-width="166" stroke-linecap="round" ' +
        'stroke-linejoin="round" clip-path="url(#cp' + i + ')"/>';
    }
    var nums = "";
    if (state.numbers) {
      var pos = layoutNumbers(d.m);
      pos.forEach(function (p, i) {
        var col = cols ? cols[i] : "var(--ink-cn)";
        nums += '<text x="' + p[0].toFixed(0) + '" y="' + p[1].toFixed(0) + '" ' +
          'text-anchor="middle" dominant-baseline="central" class="snum" fill="' + col + '">' +
          (i + 1) + '</text>';
      });
    }
    writerEl.innerHTML = gridSVG() +
      '<svg class="writer__char" viewBox="0 0 1024 1024" role="img" aria-label="' +
      d.ch + ' — animated stroke order, ' + n + ' strokes">' +
      '<defs>' + defs + '</defs>' +
      '<g transform="translate(0,900) scale(1,-1)">' + ghosts + inks + '</g>' +
      '<g class="writer__nums">' + nums + '</g></svg>';

    inkEls = $all(".ink", writerEl);
    inkEls.forEach(function (p) {
      var L = p.getTotalLength();
      p.dataset.len = L;
      p.style.strokeDasharray = L;
      p.style.strokeDashoffset = L;
    });
  }

  function showAll() {
    inkEls.forEach(function (p) {
      p.getAnimations && p.getAnimations().forEach(function (a) { a.cancel(); });
      p.style.strokeDashoffset = 0;
    });
    stepIdx = inkEls.length;
  }

  function play() {
    seqTimers.forEach(clearTimeout); seqTimers = [];
    inkEls.forEach(function (p) {
      p.getAnimations && p.getAnimations().forEach(function (a) { a.cancel(); });
      p.style.strokeDashoffset = +p.dataset.len;
    });
    if (prefersReduced) { showAll(); return; }
    stepIdx = 0;
    var i = 0;
    function next() {
      if (i >= inkEls.length) return;
      var p = inkEls[i], L = +p.dataset.len;
      var dur = clamp(220 + L * 0.34, 320, 900) / state.speed;
      p.animate([{ strokeDashoffset: L }, { strokeDashoffset: 0 }],
        { duration: dur, easing: "cubic-bezier(.45,.05,.3,1)", fill: "forwards" });
      i++; stepIdx = i;
      var t = setTimeout(next, dur + 80 / state.speed);
      seqTimers.push(t);
    }
    next();
  }

  function step() {
    seqTimers.forEach(clearTimeout); seqTimers = [];
    if (stepIdx >= inkEls.length) {            // restart from blank
      inkEls.forEach(function (p) { p.style.strokeDashoffset = +p.dataset.len; });
      stepIdx = 0;
    }
    var p = inkEls[stepIdx], L = +p.dataset.len;
    p.animate([{ strokeDashoffset: L }, { strokeDashoffset: 0 }],
      { duration: prefersReduced ? 1 : 460 / state.speed, easing: "cubic-bezier(.45,.05,.3,1)", fill: "forwards" });
    stepIdx++;
  }

  // ---- info panel ----
  var CJK = /[\u3400-\u9fff\u2e80-\u2eff\u31c0-\u31ef⺈㇏]+/g;
  function markCJK(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(CJK, function (m) { return '<span class="zh-inline">' + m + "</span>"; });
  }
  function rubyFor(seg, focus) {
    return seg.map(function (pair) {
      var ch = pair[0], py = pair[1];
      if (!py) return '<span class="punc">' + ch + "</span>";
      var cls = ch === focus ? "ru focus" : "ru";
      return '<ruby class="' + cls + '">' + ch + "<rt>" + py + "</rt></ruby>";
    }).join("");
  }

  function renderInfo(d) {
    $("#ce-py").innerHTML = d.py;
    $("#ce-en").textContent = d.en;
    $("#ce-rad").innerHTML = '<span class="zh-inline">' + d.radical + "</span> " +
      '<span class="chip__t">radical · ' + d.radEn + "</span>";
    $("#ce-strokes").innerHTML = d.s.length + ' <span class="chip__t">stroke' + (d.s.length > 1 ? "s" : "") + "</span>";
    $("#ce-origin").innerHTML = markCJK(d.origin);
    $("#ce-sentence").innerHTML = rubyFor(d.ex.seg, d.ch);
    $("#ce-sentence-en").textContent = d.ex.en;
    $("#ce-ex-lbl").textContent = d.ex.phrase ? "常用词 · A common phrase" : "举个例子 · Here's an example";

    var pos = (state.idx + 1 < 10 ? "0" : "") + (state.idx + 1);
    var tot = (DATA.length < 10 ? "0" : "") + DATA.length;
    $("#ce-pos").innerHTML = pos + ' <span class="sep">/</span> ' + tot;
    $("#ce-group").textContent = d.group;
  }

  function updateWall() {
    $all(".wall__cell").forEach(function (b, i) {
      var on = i === state.idx;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-current", on ? "true" : "false");
    });
  }

  // ---- main render ----
  function render(animate) {
    var d = DATA[state.idx];
    buildWriter(d);
    renderInfo(d);
    updateWall();
    persist();
    if (animate !== false) requestAnimationFrame(play); else showAll();
  }

  function go(delta) {
    state.idx = (state.idx + delta + DATA.length) % DATA.length;
    render(true);
    // keep active wall cell in view (horizontal scroll only — never page scroll)
    var cell = $all(".wall__cell")[state.idx];
    if (cell && cell.parentElement) {
      var wall = cell.parentElement;
      var target = cell.offsetLeft - wall.clientWidth / 2 + cell.clientWidth / 2;
      if (wall.scrollWidth > wall.clientWidth) wall.scrollTo({ left: target, behavior: "smooth" });
    }
  }

  // ---- pinyin toggle ----
  function setPinyin(on) {
    state.pinyin = on;
    document.body.classList.toggle("no-pinyin", !on);
    var btn = $("#ce-pinyin");
    if (btn) { btn.setAttribute("aria-pressed", on ? "true" : "false"); btn.classList.toggle("is-off", !on); }
    persist();
  }

  // ---- options ----
  function setOpt(key, val) {
    state[key] = val; persist();
    render(false);            // rebuild without auto-replay
    syncOptUI();
    if (key !== "speed") play();
  }
  function syncOptUI() {
    var r = $("#opt-rainbow"), n = $("#opt-numbers");
    if (r) { r.setAttribute("aria-pressed", state.rainbow); r.classList.toggle("is-on", state.rainbow); }
    if (n) { n.setAttribute("aria-pressed", state.numbers); n.classList.toggle("is-on", state.numbers); }
    $all(".speed-opt").forEach(function (b) {
      b.classList.toggle("is-on", parseFloat(b.dataset.speed) === state.speed);
    });
  }

  // ---- build the wall ----
  function buildWall() {
    var wall = $("#ce-wall");
    wall.innerHTML = DATA.map(function (d, i) {
      return '<button class="wall__cell" data-i="' + i + '" type="button" ' +
        'aria-label="' + d.ch + " " + d.py + " — " + d.en + '">' +
        '<span class="wall__ch">' + d.ch + "</span>" +
        '<span class="wall__py">' + d.py + "</span></button>";
    }).join("");
    $all(".wall__cell", wall).forEach(function (b) {
      b.addEventListener("click", function () {
        state.idx = +b.dataset.i; render(true);
      });
    });
  }

  // ---- init ----
  function init() {
    writerEl = $("#ce-writer");
    buildWall();
    setPinyin(state.pinyin);

    $("#ce-replay").addEventListener("click", play);
    $("#ce-step").addEventListener("click", step);
    $("#ce-prev").addEventListener("click", function () { go(-1); });
    $("#ce-next").addEventListener("click", function () { go(1); });
    $("#ce-pinyin").addEventListener("click", function () { setPinyin(!state.pinyin); });

    var r = $("#opt-rainbow"), n = $("#opt-numbers");
    if (r) r.addEventListener("click", function () { setOpt("rainbow", !state.rainbow); });
    if (n) n.addEventListener("click", function () { setOpt("numbers", !state.numbers); });
    $all(".speed-opt").forEach(function (b) {
      b.addEventListener("click", function () { setOpt("speed", parseFloat(b.dataset.speed)); });
    });

    // keyboard: arrows + space, only when focus isn't on a text field
    document.addEventListener("keydown", function (e) {
      if (/input|textarea|select/i.test((e.target.tagName || ""))) return;
      var stage = $("#explorer");
      var near = stage && isInView(stage);
      if (!near) return;
      if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
      else if (e.key === " " || e.key === "Enter") {
        if (e.target.closest && e.target.closest("button")) return;
        e.preventDefault(); play();
      }
    });

    syncOptUI();
    render(true);
  }

  function isInView(el) {
    var r = el.getBoundingClientRect();
    return r.top < window.innerHeight && r.bottom > 0;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
