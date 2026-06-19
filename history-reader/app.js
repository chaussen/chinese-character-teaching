/* 史案 — 史书知识图谱阅读器 · render engine (vanilla JS)
 *
 * Recreates the design handoff's full-feature wireframe in the codebase's
 * self-contained / setState+render() idiom, with the hi-fi warm-paper finish.
 *
 * Core idea (select-anywhere, highlight-everywhere): a single `sel`
 * ({kind:'term'|'lang', id}) drives every view; each view re-derives its
 * highlight from it and the bottom dock renders the matching card.
 */
(function () {
  'use strict';
  const D = window.SHI_DATA;
  const { CATS, LANG_ROLES, ENTITIES, LANG, PASSAGES } = D;
  const app = document.getElementById('app');

  const TABS = [
    ['notes', '注解'], ['timeline', '时间轴'], ['map', '地图'],
    ['rel', '关系'], ['rise', '升迁'], ['lib', '专名库']
  ];

  // ── persistent personal 专名库 (accumulates across every passage read) ──
  const LIB_KEY = 'shi.lib.v1';
  function loadLib() {
    try { return new Set(JSON.parse(localStorage.getItem(LIB_KEY) || '[]')); }
    catch (e) { return new Set(); }
  }
  function saveLib(set) {
    try { localStorage.setItem(LIB_KEY, JSON.stringify([...set])); } catch (e) {}
  }

  const state = {
    pid: PASSAGES[0].id,
    sel: null,
    tab: 'notes',
    depth: 'brief',
    langOn: true, knowOn: true, srcOn: true,
    font: 21,
    lib: loadLib()
  };

  // ── helpers ──
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  function rgba(hex, a) {
    const n = parseInt(hex.replace('#', ''), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }
  const cur = () => PASSAGES.find(p => p.id === state.pid) || PASSAGES[0];
  const catColor = c => (CATS[c] || {}).color || '#B23A2B';
  const langColor = role => LANG_ROLES[role] || '#3F6B8C';

  // unique knowledge-layer ids in order of first appearance in the passage
  function orderedTerms(p) {
    const seen = new Set(), out = [];
    for (const str of p.lines) {
      const re = /«([a-z0-9_]+)(?:\|[^»]*)?»/g; let m;
      while ((m = re.exec(str))) { if (!seen.has(m[1])) { seen.add(m[1]); out.push(m[1]); } }
    }
    return out;
  }

  // split a line into plain / «term» / ⟨lang⟩ segments.
  // Markers carry an optional surface override — «id|高祖» / ⟨id|surface⟩ — so one
  // registry entity (canonical 梁武帝) can appear under different names across texts
  // (高祖 here) while still resolving to the same id (this is the mention model).
  function parseLine(str) {
    const segs = []; let last = 0;
    const re = /«([a-z0-9_]+)(?:\|([^»]*))?»|⟨([a-z0-9_]+)(?:\|([^⟩]*))?⟩/g; let m;
    while ((m = re.exec(str))) {
      if (m.index > last) segs.push({ text: str.slice(last, m.index) });
      if (m[1]) segs.push({ text: m[2] || (ENTITIES[m[1]] || {}).w || m[1], term: m[1] });
      else segs.push({ text: m[4] || (LANG[m[3]] || {}).w || m[3], lang: m[3] });
      last = re.lastIndex;
    }
    if (last < str.length) segs.push({ text: str.slice(last) });
    return segs;
  }

  // 现代类比 (今比) anchor first, then the remaining fields
  function anchorAndFields(t) {
    const f = [...t.fields]; const i = f.findIndex(x => x.k === '今比');
    let anchor = t.brief;
    if (i >= 0) { anchor = f[i].v; f.splice(i, 1); }
    return { anchor, fields: f };
  }

  const isTermSel = id => state.sel && state.sel.kind === 'term' && state.sel.id === id;
  const isLangSel = id => state.sel && state.sel.kind === 'lang' && state.sel.id === id;

  // ════════════════════════════ views ════════════════════════════

  function viewToolbar(p) {
    const tg = (on, kind, label, sq) =>
      `<button class="toggle ${kind} ${on ? 'on' : ''}${sq ? ' sq' : ''}" data-act="toggle" data-id="${kind === 'lang' ? 'langOn' : kind === 'know' ? 'knowOn' : 'srcOn'}">
         <span class="led"></span>${label}</button>`;
    return `
    <div class="bar">
      <div class="brand">
        <span class="seal">史</span>
        <div>
          <div class="t1">史案 · 史书知识图谱阅读器</div>
          <div class="t2">${PASSAGES.length > 1
            ? `<select class="picker" data-act="passage">${PASSAGES.map(pp =>
                `<option value="${pp.id}"${pp.id === state.pid ? ' selected' : ''}>《${esc(pp.title)}》${esc(pp.sub)}</option>`).join('')}</select>`
            : `《${esc(p.title)}》${esc(p.sub)}`}</div>
        </div>
      </div>
      <span class="spacer"></span>

      ${tg(state.langOn, 'lang', '语言层', true)}
      ${tg(state.knowOn, 'know', '知识层', false)}
      <span class="divider"></span>

      <div class="grp">
        <span class="grp-label">字号</span>
        <button class="fbtn sm" data-act="font" data-id="dec" title="缩小">小</button>
        <button class="fbtn lg" data-act="font" data-id="inc" title="放大">大</button>
      </div>

      <div class="seg">
        <button class="${state.depth === 'brief' ? 'on' : ''}" data-act="depth" data-id="brief">简要</button>
        <button class="${state.depth === 'full' ? 'on' : ''}" data-act="depth" data-id="full">标准</button>
      </div>

      ${tg(state.srcOn, 'src', '溯源', false)}
    </div>`;
  }

  function viewText(p) {
    const proseStyle =
      `font-family:'Noto Serif SC',serif;font-weight:400;font-size:${state.font}px;line-height:2.35;letter-spacing:.5px;color:var(--ink);`;

    const paras = p.lines.map(line => {
      const segs = parseLine(line).map(seg => {
        if (seg.term) {
          const t = ENTITIES[seg.term]; const col = catColor(t.cat); const sel = isTermSel(seg.term);
          let st = '';
          if (state.knowOn) {
            const thick = t.cat === 'person' ? '2px' : '1.5px';
            const off = t.cat === 'office' ? '3px' : '4.5px';
            st += `text-decoration-line:underline;text-decoration-style:${CATS[t.cat].deco};text-decoration-color:${col};text-decoration-thickness:${thick};text-underline-offset:${off};`;
          }
          if (sel) st += `background:${rgba(col, .16)};color:${col};`;
          return `<span class="mark${sel ? ' sel' : ''}" style="${st}" data-act="selTerm" data-id="${seg.term}">${esc(seg.text)}</span>`;
        }
        if (seg.lang) {
          const l = LANG[seg.lang]; const col = langColor(l.role); const sel = isLangSel(seg.lang);
          let st = '';
          if (state.langOn) st += `border-bottom:2px dashed ${col};`;
          if (sel) st += `background:${rgba(col, .15)};color:${col};`;
          return `<span class="mark${sel ? ' sel' : ''}" style="${st}" data-act="selLang" data-id="${seg.lang}">${esc(seg.text)}</span>`;
        }
        return esc(seg.text);
      }).join('');
      return `<p>${segs}</p>`;
    }).join('');

    const legend = `
      <div class="legend">
        <span><b>双层标记 →</b></span>
        <span class="li"><span class="sw" style="border-bottom:2px solid var(--c-place);">专名</span>知识层（类型色）</span>
        <span class="li"><span class="sw" style="border-bottom:2px dashed var(--c-era);">虚词</span>语言层（语法·虚线）</span>
      </div>`;

    const hint = state.knowOn || state.langOn
      ? '波浪线＝地名 · 双下划线＝官职 · 点线＝年号 · 虚线＝爵位 · 实线＝人物（知识层）；语法虚线＝虚词/活用/句式（语言层）。两层各开各关，点击带标记的词即出信息卡。'
      : '两层标记已关闭，纯文阅读。开启「知识层」「语言层」后，专名与虚词将带标记，点击即出信息卡。';

    return `
    <div class="text-pane sc" data-scroll="text">
      <div class="text-inner">
        <div class="title-row">
          <span class="title-seal">${esc(p.seal)}</span>
          <div>
            <div class="tt">《${esc(p.title)}》</div>
            <div class="ts">${esc(p.sub)}</div>
          </div>
        </div>
        <p class="intro">${esc(p.intro)}</p>
        ${legend}
        <div class="prose" style="${proseStyle}">${paras}</div>
        <div class="foot-hint">${hint}</div>
      </div>
    </div>`;
  }

  // ── right panel ──
  // which tabs a passage offers (notes/lib always; the graphic views need their data)
  function availTabs(p) {
    return TABS.filter(([k]) =>
      k === 'notes' || k === 'lib' ? true :
      k === 'map' ? !!p.map :
      k === 'rel' ? !!p.rel :
      (k === 'timeline' || k === 'rise') ? !!(p.rise && p.rise.length) : true);
  }
  function viewTabs(p) {
    const n = orderedTerms(p).length;
    return `<div class="tabs sc">` + availTabs(p).map(([k, label]) => {
      const count = k === 'notes' ? `<span class="n">${n}</span>` : '';
      return `<button class="tab ${state.tab === k ? 'on' : ''}" data-act="tab" data-id="${k}">${label}${count}</button>`;
    }).join('') + `</div>`;
  }

  function viewNotes(p) {
    const ids = orderedTerms(p);
    const cards = ids.map(id => {
      const t = ENTITIES[id]; const col = catColor(t.cat); const sel = isTermSel(id);
      const cardStyle = `border-color:${sel ? rgba(col, .5) : 'var(--line)'};background:${sel ? rgba(col, .07) : 'var(--card)'};${sel ? `box-shadow:0 8px 22px -16px ${col};` : ''}`;
      const meta = !t.src
        ? `<span class="unverif">未溯源</span>`
        : (t.seen && t.seen.length ? `<span class="seen-hint">互见 ${t.seen.length}</span>` : '');
      const full = state.depth === 'full'
        ? `<div class="fields">` + t.fields.map(f =>
            `<div class="field"><span class="k" style="color:${col}">${esc(f.k)}</span><span class="v">${esc(f.v)}</span></div>`).join('') + `</div>`
        : '';
      return `
        <div class="ncard" style="${cardStyle}" data-act="selTerm" data-id="${id}">
          <div class="top">
            <span class="chip" style="background:${col}">${esc(CATS[t.cat].label)}</span>
            <span class="w">${esc(t.w)}</span>
            ${meta}
          </div>
          <div class="brief">${esc(t.brief)}</div>
          ${full}
        </div>`;
    }).join('');
    return `<div class="cards">${cards}</div>`;
  }

  function viewTimeline(p) {
    const bars = p.rise.map(r => {
      const sel = r.ref && isTermSel(r.ref);
      const col = sel ? 'var(--accent)' : 'var(--line)';
      const bg = sel ? rgba('#B23A2B', .1) : 'var(--card)';
      const title = r.title.split(' · ')[0];
      return `
        <div class="rung" data-act="selTerm" data-id="${esc(r.ref || '')}">
          <div class="rt">${esc(title)}</div>
          <div class="bar" style="height:${r.rank}%;border-color:${col};background:${bg};"></div>
          <div class="ry">${esc(r.year)}</div>
          <div class="rg">${esc(r.tag)}</div>
        </div>`;
    }).join('');
    return `
      <div class="view-h">时间轴 · 官位升降</div>
      <div class="view-sub">纵轴＝官位高低 · 横向＝时序</div>
      <div class="ladder">${bars}</div>`;
  }

  // ── geographic projection (real lng/lat → mapbox pixels) ──
  // Equirectangular fit with a cos(lat) correction so shapes stay true; the
  // window auto-zooms to each passage's points (with a min span so a tight
  // cluster still shows river/province context), preserving aspect inside the box.
  function buildProj(points, W, H) {
    const lats = points.map(p => p.ll[1]);
    const latC = (Math.min(...lats) + Math.max(...lats)) / 2;
    const k = Math.cos(latC * Math.PI / 180);          // lng compression at this latitude
    const xs = points.map(p => p.ll[0] * k);
    const ys = points.map(p => -p.ll[1]);              // y grows southward
    let cx = (Math.min(...xs) + Math.max(...xs)) / 2;
    let cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    let spanX = Math.max(Math.max(...xs) - Math.min(...xs), 3.6 * k); // ≥ ~3.6° lng
    let spanY = Math.max(Math.max(...ys) - Math.min(...ys), 3.0);     // ≥ 3° lat
    spanX *= 1.35; spanY *= 1.35;                       // breathing room around the route
    const minX = cx - spanX / 2, minY = cy - spanY / 2;
    const margin = 22;
    const sc = Math.min((W - 2 * margin) / spanX, (H - 2 * margin) / spanY);
    const offX = (W - spanX * sc) / 2, offY = (H - spanY * sc) / 2;
    return (lng, lat) => [offX + (lng * k - minX) * sc, offY + (-lat - minY) * sc];
  }

  function strokePolys(ctx, proj, polys, color, width) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    polys.forEach(line => {
      ctx.beginPath();
      line.forEach((pt, i) => { const [x, y] = proj(pt[0], pt[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.stroke();
    });
  }

  function labelRiver(ctx, proj, segs, name, color, W, H) {
    let best = null, bestd = Infinity; const cx = W * 0.5, cy = H * 0.42;
    segs.forEach(line => line.forEach(pt => {
      const [x, y] = proj(pt[0], pt[1]);
      if (x > 24 && x < W - 24 && y > 16 && y < H - 16) {
        const d = (x - cx) ** 2 + (y - cy) ** 2; if (d < bestd) { bestd = d; best = [x, y]; }
      }
    }));
    if (!best) return;
    ctx.font = '600 12px "Noto Serif SC", serif'; ctx.textBaseline = 'middle';
    ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(246,241,230,0.9)';
    ctx.strokeText(name, best[0] + 5, best[1] - 7);
    ctx.fillStyle = color; ctx.fillText(name, best[0] + 5, best[1] - 7);
  }

  // draw the base map onto the <canvas> and place HTML pins by real coordinates
  function mountMap(p) {
    const box = app.querySelector('.mapbox[data-map]'); if (!box) return;
    const cv = box.querySelector('canvas.mapcv'); if (!cv) return;
    const W = box.clientWidth, H = box.clientHeight; if (!W || !H) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px';
    const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);

    // Projection + pin placement never depend on the basemap data — if HISTORY_GEO
    // is missing (e.g. geo.js failed to load) the route still draws and pins still
    // land at their real coordinates rather than collapsing to the top-left corner.
    const proj = buildProj(p.map.points, W, H);
    const G = window.HISTORY_GEO;
    if (G) {
      const R = G.rivers;
      strokePolys(ctx, proj, G.provinces, '#DBD2BF', 1);        // 今省界 · 淡
      strokePolys(ctx, proj, R.chang, '#A9C2CE', 2.1);          // 长江
      strokePolys(ctx, proj, R.huang, '#C8B891', 2.1);          // 黄河 · 含沙色
      strokePolys(ctx, proj, R.huai, '#A9C2CE', 1.7);           // 淮河
      labelRiver(ctx, proj, R.huang, '黄河', '#B49E6C', W, H);
      labelRiver(ctx, proj, R.chang, '长江', '#7FA0AE', W, H);
      labelRiver(ctx, proj, R.huai, '淮河', '#7FA0AE', W, H);
    }

    // 行踪路线（按时序）
    const byId = {}; p.map.points.forEach(pt => byId[pt.id] = pt);
    const rp = (p.map.route || []).map(id => byId[id]).filter(Boolean);
    ctx.strokeStyle = '#8A7F66'; ctx.lineWidth = 1.8; ctx.setLineDash([5, 4]); ctx.lineJoin = 'round';
    ctx.beginPath();
    rp.forEach((pt, i) => { const [x, y] = proj(pt.ll[0], pt.ll[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.setLineDash([]);

    box.querySelectorAll('.pin').forEach(pin => {
      const ll = pin.getAttribute('data-ll').split(',').map(Number);
      const [x, y] = proj(ll[0], ll[1]);
      pin.style.left = x + 'px'; pin.style.top = y + 'px';
    });
  }

  function viewMap(p) {
    const M = p.map;
    const pins = M.points.map(pt => {
      const e = ENTITIES[pt.id];
      const sel = state.sel && (state.sel.id === pt.id || (pt.ref && state.sel.id === pt.ref));
      const col = pt.alt ? 'var(--faint)' : 'var(--accent)';
      const dot = `border:2px ${pt.alt ? 'dashed' : 'solid'} ${col};${sel ? `background:${pt.alt ? '#A99C84' : '#B23A2B'};color:#fff;` : `color:${col};`}`;
      const lab = `border-color:${sel ? (pt.alt ? '#A99C84' : '#B23A2B') : 'var(--line)'};`;
      const target = pt.ref || (ENTITIES[pt.id] ? pt.id : '');
      const w = e ? e.w : pt.id;
      return `
        <div class="pin" data-ll="${pt.ll[0]},${pt.ll[1]}" style="z-index:${sel ? 3 : 2};" data-act="selTerm" data-id="${esc(target)}">
          <span class="dot" style="${dot}">${pt.order}</span>
          <span class="lab" style="${lab}">${esc(w)}<span class="mod"> ${esc(pt.mod)}</span></span>
        </div>`;
    }).join('');

    // selected place note
    const selPin = state.sel ? M.points.find(pt => pt.id === state.sel.id || pt.ref === state.sel.id) : null;
    const note = selPin
      ? `<div class="place-note"><b>${esc((ENTITIES[selPin.id] || {}).w || selPin.id)}</b> · ${esc(selPin.mod)} · ${esc(selPin.note)}</div>`
      : '';

    return `
      <div class="view-h">地理视图 · ${esc(p.subject)}行迹</div>
      <div class="view-sub">真实经纬度底图 · 图层：水系 / 今省界 / 行踪路线</div>
      <div class="mapbox" data-map="1">
        <canvas class="mapcv"></canvas>
        <span class="stub">底图：黄河·淮河·长江 + 今省界（淡）</span>
        ${pins}
      </div>
      <div class="map-cap">${esc(M.caption)}</div>
      ${note}`;
  }

  function viewRel(p) {
    const R = p.rel;
    const edges = R.nodes.map(n =>
      `<line x1="50" y1="50" x2="${n.xy[0]}" y2="${n.xy[1]}" stroke="#A89F89" stroke-width="1.3" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"></line>`).join('');
    const labels = R.nodes.map(n => {
      const mx = 50 + (n.xy[0] - 50) * 0.5, my = 50 + (n.xy[1] - 50) * 0.5;
      return `<span class="rel-lab" style="left:${mx}%;top:${my}%;">${esc(n.rel)}</span>`;
    }).join('');
    const nodes = R.nodes.map(n => {
      const sel = isTermSel(n.id);
      const col = n.rel === '敌' ? '#B23A2B' : '#3F6B8C';
      const bub = `border-color:${col};color:${col};${sel ? `background:${rgba(col, .12)};` : ''}`;
      return `
        <div class="rel-node" style="left:${n.xy[0]}%;top:${n.xy[1]}%;" data-act="selTerm" data-id="${n.id}">
          <div class="bub" style="${bub}">${esc(n.w)}</div>
          <div class="sub">${esc(n.sub)}</div>
        </div>`;
    }).join('');
    return `
      <div class="view-h">人物关系视图</div>
      <div class="view-sub">以${esc(R.center.w)}为中心 · 点击节点 → 原文定位</div>
      <div class="relbox">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%;">${edges}</svg>
        ${labels}
        <div class="rel-center">${esc(R.center.w)}</div>
        ${nodes}
      </div>`;
  }

  function viewRise(p) {
    const steps = p.rise.map(r => {
      const col = r.ref && ENTITIES[r.ref] ? catColor(ENTITIES[r.ref].cat) : '#B23A2B';
      return `
        <div class="rstep" data-act="selTerm" data-id="${esc(r.ref || '')}">
          <span class="rdot" style="background:${col};box-shadow:0 0 0 1px ${col};"></span>
          <div class="rhead">
            <span class="ry">${esc(r.year)}</span>
            <span class="rtag">${esc(r.tag)}</span>
          </div>
          <div class="rtitle">${esc(r.title)}</div>
          <div class="rnote">${esc(r.note)}</div>
        </div>`;
    }).join('');
    return `
      <div class="view-h">${esc(p.subject)} · 权力曲线</div>
      <div class="view-sub">从北镇戍卒到陷台城——二十余年的升降</div>
      <div class="rise"><span class="spine"></span>${steps}</div>`;
  }

  function viewLib(p) {
    // accumulated across everything read; this passage's terms are merged in on load.
    const order = ['person', 'place', 'office', 'era', 'rank'];
    const byCat = {};
    [...state.lib].forEach(id => { const e = ENTITIES[id]; if (!e) return; (byCat[e.cat] = byCat[e.cat] || []).push(id); });
    const total = order.reduce((a, c) => a + (byCat[c] ? byCat[c].length : 0), 0);
    const thisCount = orderedTerms(p).length;

    const groups = order.filter(c => byCat[c]).map(c => {
      const col = catColor(c);
      const chips = byCat[c].map(id => {
        const sel = isTermSel(id);
        const st = `border:1px solid ${sel ? col : rgba(col, .35)};background:${sel ? rgba(col, .14) : 'var(--card)'};color:${col};`;
        return `<span class="libchip" style="${st}" data-act="selTerm" data-id="${id}">${esc(ENTITIES[id].w)}</span>`;
      }).join('');
      return `
        <div class="libgroup">
          <div class="gh"><span class="gsw" style="background:${col}"></span>
            <span class="gl">${esc(CATS[c].label)}</span><span class="gc" style="color:${col}">${byCat[c].length}</span></div>
          <div class="libchips">${chips}</div>
        </div>`;
    }).join('');

    return `
      <div class="view-h">个人专名库</div>
      <div class="view-sub">本机累计 ${total} · 本篇 ${thisCount} · 每读一篇自动增补，跨篇按互见聚合</div>
      <div class="libgroups">${groups}</div>`;
  }

  function viewPanel(p) {
    const body =
      state.tab === 'notes' ? viewNotes(p) :
      state.tab === 'timeline' ? viewTimeline(p) :
      state.tab === 'map' ? viewMap(p) :
      state.tab === 'rel' ? viewRel(p) :
      state.tab === 'rise' ? viewRise(p) :
      viewLib(p);
    return `<div class="panel">${viewTabs(p)}<div class="panel-body sc" data-scroll="panel">${body}</div></div>`;
  }

  // ── bottom detail dock ──
  function viewDock() {
    if (!state.sel) {
      return `<div class="dock"><div class="dock-empty"><span class="ed"></span>点击原文中带标记的词 → 这里显示信息卡。专名出知识层卡，虚词 / 活用出语言层卡。</div></div>`;
    }
    if (state.sel.kind === 'term') {
      const t = ENTITIES[state.sel.id]; if (!t) return `<div class="dock"></div>`;
      const col = catColor(t.cat); const af = anchorAndFields(t);
      const srcLine = state.srcOn
        ? `<span class="src">${t.src ? '溯源：' + esc(t.src) : '<span class="nosrc">未溯源 · 待考</span>'}</span>`
        : '';
      const grid = `<div class="dock-grid">` + af.fields.map(f =>
        `<div class="field"><span class="k" style="width:2.8em;color:${col}">${esc(f.k)}</span><span class="v">${esc(f.v)}</span></div>`).join('') + `</div>`;
      const seealso = (t.seen && t.seen.length)
        ? `<div class="seealso"><span class="lbl">互见 →</span>` + t.seen.map(s =>
            `<span class="xref" title="跨篇跳转（待接入互见引擎）" data-act="xref">《${esc(s)}》</span>`).join('') + `</div>`
        : '';
      return `
        <div class="dock"><div class="dock-card sc">
          <div class="dock-head">
            <span class="chip" style="background:${col}">${esc(CATS[t.cat].label)}</span>
            <span class="w">${esc(t.w)}</span>
            <span class="anchor">＝ ${esc(af.anchor)}</span>
            ${srcLine}
          </div>
          ${grid}
          ${seealso}
        </div></div>`;
    }
    // language card
    const l = LANG[state.sel.id]; if (!l) return `<div class="dock"></div>`;
    const col = langColor(l.role);
    const srcLine = state.srcOn && l.src ? `<span class="src">溯源：${esc(l.src)}</span>` : '';
    return `
      <div class="dock"><div class="dock-card sc">
        <div class="dock-head">
          <span class="chip" style="background:transparent;color:${col};border:1px dashed ${col};">语言层 · ${esc(l.roleFull)}</span>
          <span class="w">${esc(l.w)}</span>
          <span class="anchor">（${esc(l.sub)}）</span>
          ${srcLine}
        </div>
        <div class="dock-gloss">${esc(l.gloss)}</div>
      </div></div>`;
  }

  // ════════════════════════════ render ════════════════════════════
  function render() {
    const p = cur();
    // a passage may not offer the active tab (e.g. no career timeline) — fall back
    if (!availTabs(p).some(([k]) => k === state.tab)) state.tab = 'notes';
    // preserve scroll positions across full re-render
    const saved = {};
    app.querySelectorAll('[data-scroll]').forEach(el => saved[el.getAttribute('data-scroll')] = el.scrollTop);

    app.innerHTML =
      viewToolbar(p) +
      `<div class="body">${viewText(p)}${viewPanel(p)}</div>` +
      viewDock();

    app.querySelectorAll('[data-scroll]').forEach(el => {
      const v = saved[el.getAttribute('data-scroll')]; if (v != null) el.scrollTop = v;
    });

    if (state.tab === 'map') mountMap(p);
  }

  // keep the canvas base map crisp / pins registered when the panel resizes
  let mapRAF = 0;
  window.addEventListener('resize', () => {
    if (state.tab !== 'map') return;
    cancelAnimationFrame(mapRAF);
    mapRAF = requestAnimationFrame(() => mountMap(cur()));
  });

  function setState(patch) { Object.assign(state, patch); render(); }

  // ── events (delegated) ──
  app.addEventListener('click', e => {
    const el = e.target.closest('[data-act]'); if (!el) return;
    const act = el.getAttribute('data-act');
    const id = el.getAttribute('data-id');
    switch (act) {
      case 'selTerm':
        if (id && ENTITIES[id]) setState({ sel: { kind: 'term', id } });
        break;
      case 'selLang':
        if (id && LANG[id]) setState({ sel: { kind: 'lang', id } });
        break;
      case 'tab': setState({ tab: id }); break;
      case 'toggle': setState({ [id]: !state[id] }); break;
      case 'depth': setState({ depth: id }); break;
      case 'font':
        setState({ font: id === 'inc' ? Math.min(28, state.font + 2) : Math.max(15, state.font - 2) });
        break;
      case 'xref':
        // cross-text jump is stubbed in the prototype (needs the 互见 engine)
        break;
    }
  });

  // merge a passage's terms into the persistent 专名库 (accumulates across reads)
  function mergeLib(p) {
    let changed = false;
    orderedTerms(p).forEach(id => { if (!state.lib.has(id)) { state.lib.add(id); changed = true; } });
    if (changed) saveLib(state.lib);
  }

  // passage switch (corpus nav): reset selection/tab, accrue the new passage's terms
  app.addEventListener('change', e => {
    const el = e.target.closest('select[data-act="passage"]'); if (!el) return;
    if (PASSAGES.some(p => p.id === el.value)) {
      state.pid = el.value;
      mergeLib(cur());
      setState({ sel: null, tab: 'notes' });
    }
  });

  // ── boot: merge this passage's terms into the persistent 专名库 ──
  (function boot() {
    mergeLib(cur());
    render();
  })();
})();
