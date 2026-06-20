/* app.js — 学写字 · Character Studio engine (vanilla, no deps).
   Lock → Home(bands) → Units → Deck → Learn / Practice.
   Stroke brush ported from the Casey character explorer (makemeahanzi 1024 Y-up). */
(function () {
  "use strict";
  var DATA = (window.APP_DATA && window.APP_DATA.bands) || [];
  var LS = "ccs-studio-v1";
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return [].slice.call((r || document).querySelectorAll(s)); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;"); }
  var EXTRA = window.CONTENT_EXTRA || {};
  function extraOf(ch){ return EXTRA[ch] || null; }
  var RADS = window.RADICALS || {};
  // strip the " (名称)" / trailing "." / " / x" some source radicals carry, to the base glyph
  function radBase(r){ if(!r) return ""; return String(r).split("(")[0].split("/")[0].replace(/[.\s]/g,"").trim(); }
  function radInfo(ch){
    var c = CHAR_INDEX[ch] || {}, base = radBase(c.radical);
    var info = RADS[base] || null;
    var en = (c.radEn) || (info && info.en) || "";
    return { glyph: base || (c.radical||""), en: en, cn: info&&info.cn, note: info&&info.note };
  }

  // master index: ch -> full char object (must carry stroke data). Built from
  // the curriculum bands + the general library; powers the Library collections.
  var CHAR_INDEX = {};
  function indexChar(c){ if(c && c.ch && !CHAR_INDEX[c.ch]) CHAR_INDEX[c.ch] = c; }
  function buildIndex(){
    DATA.forEach(function(b){ b.units.forEach(function(u){ u.chars.forEach(indexChar); }); });
    var G=(window.GENERAL_DATA&&window.GENERAL_DATA.groups)||[]; G.forEach(function(g){ g.chars.forEach(indexChar); });
    // stroke-data-only pool feeding the Library books (no Home theme of its own).
    var LC=(window.LIBRARY_CHARS&&window.LIBRARY_CHARS.chars)||[]; LC.forEach(indexChar);
  }

  // ── audio: play a recorded file if the teacher has supplied one, else fall
  //    back to the browser's built-in Chinese text-to-speech (read-aloud). ──
  //    window.AUDIO_INDEX (optional, see audio-index.js) lists which recordings
  //    exist, so we never fire a 404 for a missing file. Empty/absent = all TTS.
  var audioToastT=null, ttsVoice=null;
  function pickVoice(){
    if(!window.speechSynthesis) return null;
    var vs = speechSynthesis.getVoices()||[];
    ttsVoice = vs.filter(function(v){ return /zh|cmn|Chinese/i.test(v.lang+" "+v.name); })[0] || ttsVoice;
    return ttsVoice;
  }
  if (window.speechSynthesis){ pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
  function speak(text){
    if(!window.speechSynthesis) return false;
    try{ speechSynthesis.cancel(); var u=new SpeechSynthesisUtterance(text);
      u.lang="zh-CN"; u.rate=.8; if(ttsVoice||pickVoice()) u.voice=ttsVoice;
      speechSynthesis.speak(u); return true; }catch(e){ return false; }
  }
  function hasRecording(kind,key){ var I=window.AUDIO_INDEX; return !!(I && I[kind] && I[kind][key]); }
  function toast(text, sub){ var t=$("#audio-toast"); if(!t) return;
    t.innerHTML='<span class="zh">'+esc(text)+'</span> · '+sub; t.classList.add("show");
    clearTimeout(audioToastT); audioToastT=setTimeout(function(){ t.classList.remove("show"); },1600); }
  function playAudio(kind, key, label){
    // `label` is what the toast shows — defaults to the audio key (the character),
    // but exercises that hide the character (e.g. listen & choose) pass pinyin so
    // the toast doesn't leak the answer.
    var shown = label || key;
    if (hasRecording(kind,key)){
      var a=new Audio('audio/'+kind+'/'+encodeURIComponent(key)+'.mp3');
      a.play().then(function(){ toast(shown,'playing'); }).catch(function(){ if(speak(key)) toast(shown,'read aloud'); });
    } else if (speak(key)){ toast(shown,'read aloud'); }
    else { toast(shown,'audio coming soon'); }
  }

  // ───────── persistence ─────────
  var store = { mastery:{}, learn:{ rainbow:true, numbers:true, speed:1, pinyin:true }, last:null };
  try { var s = JSON.parse(localStorage.getItem(LS)); if (s) store = Object.assign(store, s), store.learn = Object.assign({ rainbow:true, numbers:true, speed:1, pinyin:true }, s.learn||{}); } catch(e){}
  function save(){ try{ localStorage.setItem(LS, JSON.stringify(store)); }catch(e){} schedulePush(); }
  function keyOf(band, ch){ return band + ":" + ch; }
  function isKnown(band, ch){ return !!store.mastery[keyOf(band,ch)]; }
  function masteredCount(bandId, unit){
    var b = bandById(bandId); var n = 0;
    b.units.forEach(function(u){ if (unit && u.n !== unit) return; u.chars.forEach(function(c){ if (isKnown(bandId, c.ch)) n++; }); });
    return n;
  }
  var GEN_BAND = null, GEN_THEMES = [], LIB = {}, LIB_SERIES = [];
  function buildGenBand(){
    var G = (window.GENERAL_DATA && window.GENERAL_DATA.groups) || [];
    GEN_BAND = { id:'GEN', name:'General Characters', cnpy:[["通","tōng"],["用","yòng"],["汉","hàn"],["字","zì"],], isGen:true,
      glyph:'字', pigment:{glyph:'字', name:'Free practice'}, accent:'#3E7C8C', accentSoft:'#C2DBE1', tint:'#E6F0F3',
      total: G.reduce(function(s,g){ return s+g.chars.length; }, 0),
      units: G.map(function(g,i){ return { n:i+1, title:g.title, chars:g.chars }; }) };
  }
  // Extension learning is browsed as theme groups: one card per General theme,
  // each deep-linking straight to that theme's characters. Curated glyph+accent
  // per theme keep the grid lively; an unlisted theme falls back to the GEN teal.
  function buildGenThemes(){
    var STYLE = {
      "数字":  {g:"三", a:"#C2473C", s:"#F4C9C3", t:"#FBE7E3"},
      "人和家": {g:"人", a:"#C77F2E", s:"#F0D6AE", t:"#FBEFDC"},
      "身体":  {g:"手", a:"#B5566B", s:"#EAC5CF", t:"#F8E8ED"},
      "大自然": {g:"山", a:"#4E8A5B", s:"#C2DDC8", t:"#E6F1E9"},
      "动物":  {g:"鸟", a:"#7A6BBE", s:"#D3CCEC", t:"#ECE8F7"},
      "时间":  {g:"日", a:"#3E7C8C", s:"#C2DBE1", t:"#E6F0F3"},
      "方位":  {g:"上", a:"#8A7340", s:"#DACBA0", t:"#F1EAD7"},
      "颜色":  {g:"红", a:"#C44E8B", s:"#EFC4DA", t:"#FAE7F1"},
      "动作":  {g:"走", a:"#2F7E6F", s:"#BADBD3", t:"#E3F0EC"},
      "常用字": {g:"字", a:"#6E7687", s:"#CDD2DB", t:"#EEF0F3"}
    };
    var DEF = { g:"字", a:"#3E7C8C", s:"#C2DBE1", t:"#E6F0F3" };
    GEN_THEMES = (GEN_BAND ? GEN_BAND.units : []).map(function(u){
      var p = String(u.title).split("·"), cn=(p[0]||"").trim(), en=(p[1]||"").trim();
      var st = STYLE[cn] || DEF;
      return { n:u.n, cn:cn, en:en||cn, glyph:st.g, accent:st.a, accentSoft:st.s, tint:st.t, total:u.chars.length };
    });
  }
  // resolve each library series' Hanzi lists into full char objects via CHAR_INDEX.
  // Characters without bundled stroke data are dropped (and logged) — house rule.
  function buildLibrary(){
    var ser = (window.LIBRARY_DATA && window.LIBRARY_DATA.series) || [];
    ser.forEach(function(S){
      var bookIds=[];
      (S.books||[]).forEach(function(col){
        var missing=[], total=0;
        var units = col.lessons.map(function(l){
          var chars=[];
          l.chars.forEach(function(ch){ var c=CHAR_INDEX[ch]; if(c){ chars.push(c); total++; } else missing.push(ch); });
          return { n:l.n, title:l.title, chars:chars };
        }).filter(function(u){ return u.chars.length; });
        if (missing.length) console.warn('[Library '+col.id+'] no stroke data, skipped: '+missing.join(' '));
        LIB[col.id] = { id:col.id, name:col.title, cn:col.cn, cnpy:col.cnpy, vol:col.vol, sub:col.sub, isLib:true,
          glyph:col.glyph, pigment:{glyph:col.glyph, name:col.pigment}, accent:col.accent, accentSoft:col.accentSoft, tint:col.tint,
          total:total, units:units };
        bookIds.push(col.id);
      });
      LIB_SERIES.push({ id:S.id, cn:S.cn, cnpy:S.cnpy, en:S.en, sub:S.sub, bookIds:bookIds });
    });
  }
  function libList(){ return Object.keys(LIB).map(function(k){ return LIB[k]; }); }
  function bandById(id){ if(id==='GEN'){ return GEN_BAND; } if(LIB[id]) return LIB[id]; return DATA.filter(function(b){ return b.id===id; })[0]; }
  function bookLabel(id){ return id==='GEN' ? 'General' : (LIB[id]?LIB[id].name:('Book '+id.slice(1))); }

  // ── Home is grouped by SERIES → BOOK; every book renders the same card ──
  function buildSections(){
    var secs = [];
    secs.push({ cn:'凯西中文学校', cnpy:[["凯","kǎi"],["西","xī"],["中","zhōng"],["文","wén"]], en:'Our school course',
      sub:'The four-book Foundation series', books: DATA.map(function(b){ return {
        id:b.id, accent:b.accent, accentSoft:b.accentSoft, tint:b.tint, glyph:b.pigment.glyph, pigmentName:b.pigment.name,
        eyebrow:'Book '+b.id.slice(1)+' · '+b.name, titleEn:b.name, cnpy:b.cnpy, unitWord:'units', total:b.total, unitsLen:b.units.length };
      }) });
    LIB_SERIES.forEach(function(S){
      secs.push({ cn:S.cn, cnpy:S.cnpy, en:S.en, sub:S.sub, books: S.bookIds.map(function(id){ var b=LIB[id]; return {
        id:b.id, accent:b.accent, accentSoft:b.accentSoft, tint:b.tint, glyph:b.glyph, pigmentName:b.pigment.name,
        eyebrow:b.vol||'Library', titleEn:b.name, cnpy:b.cnpy, unitWord:'lessons', total:b.total, unitsLen:b.units.length };
      }) });
    });
    secs.push({ cn:'通用汉字', cnpy:[["通","tōng"],["用","yòng"],["汉","hàn"],["字","zì"]], en:'General characters',
      sub:'Extra characters for extension learning — pick a theme.', themes: GEN_THEMES });
    return secs;
  }

  // ───────── per-band accent theming ─────────
  function applyAccent(b){
    var r = document.documentElement.style;
    if (!b){ r.setProperty("--accent","#C2473C"); r.setProperty("--accent-soft","#F4C9C3"); r.setProperty("--accent-tint","#FBE7E3"); return; }
    r.setProperty("--accent", b.accent); r.setProperty("--accent-soft", b.accentSoft); r.setProperty("--accent-tint", b.tint);
  }

  // ───────── routing ─────────
  var nav = { band:null, unit:null, deck:[], idx:0 };
  function showView(name){
    $all(".view").forEach(function(v){ v.classList.toggle("is-active", v.id === "view-"+name); });
  }

  // ═════════ AUTH (Cloudflare Worker + D1 backend — see backend/README.md) ═════════
  var API_BASE = window.STUDIO_API_BASE || "";
  function api(path, opts){
    opts = opts || {};
    return fetch(API_BASE + path, Object.assign({ credentials:"include", headers:{ "Content-Type":"application/json" } }, opts))
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(body){ return { ok:r.ok, status:r.status, body:body }; }); });
  }
  var session = null; // { username, class_name, role }
  var pushTimer = null;
  function schedulePush(){
    if (!session || !API_BASE) return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(function(){
      api("/api/progress", { method:"PUT", body: JSON.stringify({ data: { mastery:store.mastery, learn:store.learn, last:store.last } }) });
    }, 800);
  }

  function setAuthError(msg){ var e=$("#auth-error"); if(e) e.textContent = msg || ""; }
  function setAuthMode(signup){
    var form = $("#auth-form"); if(!form) return;
    form.classList.toggle("is-signup", signup);
    $("#auth-submit").textContent = signup ? "Sign up" : "Log in";
    $("#auth-toggle").textContent = signup ? "Have an account? Log in" : "Need an account? Sign up";
    setAuthError("");
  }
  function bindAuth(){
    var form = $("#auth-form"); if(!form) return;
    $("#auth-toggle").addEventListener("click", function(){ setAuthMode(!form.classList.contains("is-signup")); });
    form.addEventListener("submit", function(e){
      e.preventDefault();
      var username = $("#auth-username").value.trim();
      var password = $("#auth-password").value;
      var className = $("#auth-class").value.trim();
      var signup = form.classList.contains("is-signup");
      var btn = $("#auth-submit"); btn.disabled = true; setAuthError("");
      api(signup ? "/api/signup" : "/api/login", {
        method:"POST",
        body: JSON.stringify(signup ? { username:username, password:password, class_name:className } : { username:username, password:password })
      }).then(function(res){
        btn.disabled = false;
        if (!res.ok){ setAuthError(res.body.error || "Something went wrong."); return; }
        session = res.body;
        afterLogin();
      }).catch(function(){ btn.disabled = false; setAuthError("Couldn't reach the server — check your connection."); });
    });
  }

  function afterLogin(){
    api("/api/progress").then(function(res){
      if (res.ok && res.body.data){
        var d = res.body.data;
        if (d.mastery) store.mastery = d.mastery;
        if (d.learn) store.learn = Object.assign(store.learn, d.learn);
        if (d.last) store.last = d.last;
        save();
      }
      enterApp();
    });
  }

  function enterApp(){ applyAccent(null); buildHome(); showView("home"); }
  function lockApp(){
    session = null;
    if (API_BASE) api("/api/logout", { method:"POST" });
    var form = $("#auth-form"); if(form) form.reset();
    setAuthError(""); showView("lock");
  }

  // ═════════ HOME (series → books) ═════════
  function ruby(pairs){ return pairs.map(function(p){ return "<ruby>"+p[0]+"<rt>"+p[1]+"</rt></ruby>"; }).join(""); }
  function bookCard(b){
    var done = masteredCount(b.id), pct = b.total?Math.round(done/b.total*100):0;
    return '<button class="bookcard" data-band="'+b.id+'" style="--bc:'+b.accent+';--bc-soft:'+b.accentSoft+';--bc-tint:'+b.tint+'">'+
      '<div class="bookcard__pig"><span class="g zh">'+b.glyph+'</span><span class="nm">'+esc(b.pigmentName)+'</span></div>'+
      '<div class="bookcard__body">'+
        '<div class="bookcard__ey">'+esc(b.eyebrow)+'</div>'+
        '<div class="bookcard__title">'+esc(b.titleEn)+' <span class="zh">'+ruby(b.cnpy)+'</span></div>'+
        '<div class="bookcard__foot">'+
          '<span class="bookcard__cnt"><b>'+done+'</b> / '+b.total+' learned · '+b.unitsLen+' '+b.unitWord+'</span>'+
          '<span class="bar"><i style="width:'+pct+'%"></i></span>'+
        '</div>'+
      '</div><div class="bookcard__arrow">→</div></button>';
  }
  // a theme group card (extension learning) — same shell as a book card, but it
  // deep-links into one General theme and tracks that theme's own progress.
  function themeCard(t){
    var done = masteredCount('GEN', t.n), pct = t.total?Math.round(done/t.total*100):0;
    return '<button class="bookcard themecard" data-band="GEN" data-unit="'+t.n+'" style="--bc:'+t.accent+';--bc-soft:'+t.accentSoft+';--bc-tint:'+t.tint+'">'+
      '<div class="bookcard__pig"><span class="g zh">'+t.glyph+'</span><span class="nm">'+t.total+' 字</span></div>'+
      '<div class="bookcard__body">'+
        '<div class="bookcard__ey">Theme · 主题</div>'+
        '<div class="bookcard__title">'+esc(t.en)+' <span class="zh">'+esc(t.cn)+'</span></div>'+
        '<div class="bookcard__foot">'+
          '<span class="bookcard__cnt"><b>'+done+'</b> / '+t.total+' learned</span>'+
          '<span class="bar"><i style="width:'+pct+'%"></i></span>'+
        '</div>'+
      '</div><div class="bookcard__arrow">→</div></button>';
  }
  function buildHome(){
    var host = $("#home-sections");
    host.innerHTML = buildSections().map(function(sec){
      var cards = sec.themes ? sec.themes.map(themeCard).join('') : sec.books.map(bookCard).join('');
      return '<section class="hsec">'+
        '<div class="hsec__head"><h2 class="hsec__title">'+esc(sec.en)+' <span class="zh">'+ruby(sec.cnpy)+'</span></h2>'+
        '<p class="hsec__sub">'+esc(sec.sub)+'</p></div>'+
        '<div class="bookgrid">'+ cards +'</div></section>';
    }).join("");
    $all(".bookcard", host).forEach(function(c){ c.addEventListener("click", function(){
      if (c.dataset.unit) openGenTheme(+c.dataset.unit); else openBand(c.dataset.band);
    }); });
    var tot=0, done=0; DATA.forEach(function(b){ tot+=b.total; done+=masteredCount(b.id); });
    $("#home-progress").innerHTML = '<b>'+done+'</b> of '+tot+' characters';
  }

  // ═════════ UNITS ═════════
  function openBand(id){
    nav.band = id; var b = bandById(id); applyAccent(b);
    var gen = id==='GEN', lib = !!b.isLib, virt = gen || lib;
    $("#units-title").innerHTML = gen ? 'General Characters <span class="zh">通用汉字</span>'
      : lib ? (esc(b.name)+' <span class="zh">'+rubyInline(b.cnpy)+'</span>')
      : ("Book "+id.slice(1)+' · '+b.name+' <span class="zh">'+rubyInline(b.cnpy)+'</span>');
    $("#units-band-pill").innerHTML = gen ? '通用' : (b.pigment.glyph + ' <span style="opacity:.7">'+b.pigment.name+'</span>');
    var done = masteredCount(id);
    $("#units-progress").innerHTML = '<b>'+done+'</b> / '+b.total+' learned';
    $("#units-practice").innerHTML = '<span class="ic">✎</span> ' + (virt ? 'Exercises for the whole set' : 'Exercises for the whole book');
    var grid = $("#unitgrid");
    grid.innerHTML = b.units.map(function(u){
      var preview = u.chars.slice(0,6).map(function(c){ return c.ch; }).join("");
      var more = u.chars.length>6 ? '<span style="font-size:14px;color:var(--ink-mute);align-self:flex-end">+'+(u.chars.length-6)+'</span>' : "";
      var dn = u.chars.filter(function(c){return isKnown(id,c.ch);}).length;
      return '<button class="unitcard" data-unit="'+u.n+'">'+
        '<div class="unitcard__n">'+(virt ? esc(u.title) : ('Unit '+u.n))+'</div>'+
        '<div class="unitcard__chs">'+preview+more+'</div>'+
        '<div class="unitcard__foot"><span class="unitcard__cnt">'+dn+'/'+u.chars.length+' learned</span>'+
        '<span class="bar" style="max-width:90px"><i style="width:'+Math.round(dn/u.chars.length*100)+'%"></i></span></div>'+
        '</button>';
    }).join("");
    grid.querySelectorAll(".unitcard").forEach(function(c){
      c.addEventListener("click", function(){ openUnit(id, +c.dataset.unit); });
    });
    showView("units");
  }
  // jump straight from a theme group card into its characters, carrying the
  // theme's accent through the deck/learn views.
  function openGenTheme(n){
    var t = GEN_THEMES.filter(function(x){ return x.n===n; })[0];
    if (t) applyAccent({ accent:t.accent, accentSoft:t.accentSoft, tint:t.tint });
    openUnit('GEN', n);
  }
  function rubyInline(pairs){ return pairs.map(function(p){ return "<ruby>"+p[0]+"<rt>"+p[1]+"</rt></ruby>"; }).join(""); }

  // ═════════ DECK ═════════
  function unitOf(bandId, n){ return bandById(bandId).units.filter(function(u){return u.n===n;})[0]; }
  function openUnit(bandId, n){
    nav.band = bandId; nav.unit = n; store.last = { band:bandId, unit:n }; save();
    var u = unitOf(bandId, n);
    var b = bandById(bandId), gen = bandId==='GEN', virt = gen || !!b.isLib;
    $("#deck-title").innerHTML = virt ? (esc(u.title)) : ("Unit "+n+' <span class="zh">学写字</span>');
    $("#deck-sub").textContent = u.chars.length + (virt ? " characters · tap to learn" : " characters to write");
    var grid = $("#deckgrid");
    grid.innerHTML = u.chars.map(function(c, i){
      var known = isKnown(bandId, c.ch);
      return '<button class="tile'+(known?' known':'')+'" data-i="'+i+'">'+
        (c.further?'<span class="tile__further">home</span>':'')+
        '<span class="tile__star">'+(known?'★':'☆')+'</span>'+
        '<span class="tile__ch">'+c.ch+'</span>'+
        '<span class="tile__py">'+c.py+'</span>'+
        '<span class="tile__en">'+esc(c.en)+'</span></button>';
    }).join("");
    grid.querySelectorAll(".tile").forEach(function(t){
      t.addEventListener("click", function(){ openLearn(u.chars, +t.dataset.i); });
    });
    showView("deck");
  }

  // ═════════ WRITER ENGINE ═════════
  function palette(n){ var o=[]; for(var i=0;i<n;i++){ var t=n<=1?0:i/(n-1); o.push("hsl("+(8+t*282).toFixed(1)+" 64% 47%)"); } return o; }
  function medianPath(m){ return "M " + m.map(function(p){ return p[0]+" "+p[1]; }).join(" L "); }

  // ═════════ HANDWRITING RECOGNITION ═════════
  // Match a hand-drawn stroke against an expected stroke median. Everything is in
  // the 1024 Y-up data space (the same space as char.m / char.s), so callers just
  // convert pointer coords once. Returns a verdict plus the raw geometry measures
  // so the UI can give targeted feedback (start / end / direction / shape / length).
  function _dist(a,b){ var dx=a[0]-b[0], dy=a[1]-b[1]; return Math.sqrt(dx*dx+dy*dy); }
  function _polyLen(p){ var L=0; for(var i=1;i<p.length;i++) L+=_dist(p[i-1],p[i]); return L; }
  function _resample(p, n){
    if(p.length<2) p=[p[0]||[0,0], [(p[0]?p[0][0]:0)+0.01, (p[0]?p[0][1]:0)+0.01]];
    var L=_polyLen(p)||1, step=L/(n-1), out=[p[0].slice()], acc=0, prev=p[0], i=1;
    while(out.length<n && i<p.length){
      var seg=_dist(prev,p[i]);
      if(acc+seg>=step && seg>1e-6){
        var t=(step-acc)/seg, np=[prev[0]+(p[i][0]-prev[0])*t, prev[1]+(p[i][1]-prev[1])*t];
        out.push(np); prev=np; acc=0;
      } else { acc+=seg; prev=p[i]; i++; }
    }
    while(out.length<n) out.push(p[p.length-1].slice());
    return out;
  }
  // discrete Fréchet distance between two equal-length resampled curves
  function _frechet(P,Q){
    var n=P.length, m=Q.length, ca=[];
    for(var a=0;a<n;a++){ ca.push(new Array(m)); for(var b=0;b<m;b++) ca[a][b]=-1; }
    function c(i,j){
      if(ca[i][j]>-1) return ca[i][j];
      var d=_dist(P[i],Q[j]);
      if(i===0&&j===0) ca[i][j]=d;
      else if(i>0&&j===0) ca[i][j]=Math.max(c(i-1,0),d);
      else if(i===0&&j>0) ca[i][j]=Math.max(c(0,j-1),d);
      else ca[i][j]=Math.max(Math.min(c(i-1,j),c(i-1,j-1),c(i,j-1)),d);
      return ca[i][j];
    }
    return c(n-1,m-1);
  }
  function _dir(p){ var a=p[0], b=p[p.length-1], dx=b[0]-a[0], dy=b[1]-a[1], L=Math.hypot(dx,dy)||1; return [dx/L,dy/L]; }
  function strokeMatch(userPts, median, opts){
    opts = opts || {};
    var SIZE = opts.size || 1024, N = 16;
    // drop jitter-duplicate points
    var u=[]; for(var i=0;i<userPts.length;i++){ if(!u.length || _dist(userPts[i],u[u.length-1])>1) u.push(userPts[i]); }
    if(u.length<1) u=userPts.slice();
    if(!u.length || !median || !median.length) return { match:false, reason:'empty', frechet:1, startDist:1, endDist:1, dirSim:0, lenRatio:0, isDot:false };
    var uLen=_polyLen(u), mLen=_polyLen(median);
    var frechet=_frechet(_resample(u,N), _resample(median,N))/SIZE;
    var isDot=(mLen/SIZE)<0.12;
    var sF=_dist(u[0],median[0])/SIZE, eF=_dist(u[u.length-1],median[median.length-1])/SIZE;
    var startDist=sF, endDist=eF;
    if(opts.anyDir){ var sR=_dist(u[0],median[median.length-1])/SIZE, eR=_dist(u[u.length-1],median[0])/SIZE;
      if(sR+eR < sF+eF){ startDist=sR; endDist=eR; } }
    var du=_dir(u), dm=_dir(median), dirSim=du[0]*dm[0]+du[1]*dm[1]; if(opts.anyDir) dirSim=Math.abs(dirSim);
    var lenRatio = mLen>1 ? uLen/mLen : 1;
    var FR=opts.frechet||0.34, SE=opts.startEnd||0.28, DIR=(opts.dir!=null?opts.dir:0.20);
    // Position tolerance scales with stroke size. A flat box is far bigger than a
    // dot and bigger than the gaps between closely-packed strokes (e.g. the four
    // dots in 雨), so tiny strokes were accepted anywhere in the middle. Tighten
    // the box for short strokes — position is their only cue — while long strokes
    // keep the generous tolerance so normal tracing isn't made harder. Only the
    // ordered (trace) path tightens; the free-sketch grader (anyDir) stays lenient.
    var mFrac = mLen/SIZE;
    var posTol = opts.anyDir ? SE
               : isDot ? Math.min(SE, 0.13) : Math.min(SE, Math.max(0.16, 0.13 + 0.30*mFrac));
    var okEnds=startDist<=posTol && endDist<=posTol, okDir=isDot||dirSim>=DIR,
        okShape=frechet<=FR, okLen=isDot||(lenRatio>=0.28 && lenRatio<=2.6);
    // A wildly wrong length is the clearest signal you're drawing a different
    // stroke than expected (e.g. a dot where a long stroke is wanted), so report
    // it ahead of a start/end miss for a more useful tip.
    var grossLen = !isDot && mLen>1 && (lenRatio<0.45 || lenRatio>2.4);
    var reason = grossLen ? 'length' : !okEnds ? (startDist>posTol?'start':'end') : !okDir ? 'direction' : !okShape ? 'shape' : !okLen ? 'length' : 'ok';
    return { match:okEnds&&okDir&&okShape&&okLen, reason:reason, frechet:frechet,
             startDist:startDist, endDist:endDist, dirSim:dirSim, lenRatio:lenRatio, isDot:isDot };
  }

  function gridSVG(){
    return '<svg class="writer__grid" viewBox="0 0 1024 1024" aria-hidden="true">'+
      '<rect x="3" y="3" width="1018" height="1018" rx="10" fill="none" class="g-frame"/>'+
      '<line class="g-dash" x1="512" y1="14" x2="512" y2="1010"/>'+
      '<line class="g-dash" x1="14" y1="512" x2="1010" y2="512"/>'+
      '<line class="g-diag" x1="40" y1="40" x2="984" y2="984"/>'+
      '<line class="g-diag" x1="984" y1="40" x2="40" y2="984"/></svg>';
  }
  function layoutNumbers(medians){
    var orig = medians.map(function(m){ return [m[0][0], 900-m[0][1]]; });
    var pos = orig.map(function(p){ return [p[0],p[1]]; });
    var R=104;
    for(var it=0;it<90;it++){
      for(var i=0;i<pos.length;i++) for(var j=i+1;j<pos.length;j++){
        var dx=pos[j][0]-pos[i][0], dy=pos[j][1]-pos[i][1], dist=Math.hypot(dx,dy)||0.01;
        if(dist<R){ var push=(R-dist)/2; dx/=dist; dy/=dist; pos[i][0]-=dx*push; pos[i][1]-=dy*push; pos[j][0]+=dx*push; pos[j][1]+=dy*push; }
      }
      for(var k=0;k<pos.length;k++){ pos[k][0]+=(orig[k][0]-pos[k][0])*0.06; pos[k][1]+=(orig[k][1]-pos[k][1])*0.06; }
    }
    pos.forEach(function(p){ p[0]=clamp(p[0],60,964); p[1]=clamp(p[1],60,964); });
    return pos;
  }
  // Reveal a stroke by tweening its stroke-dashoffset L→0 via requestAnimationFrame.
  // We do this by hand rather than via element.animate(): Firefox doesn't reliably
  // animate stroke-dashoffset (an SVG presentation attribute) through the Web
  // Animations API, which left the stroke player static there. rAF + inline style
  // works in every browser. Returns a handle with .cancel(). Honours reduced motion.
  function tweenDash(p, dur, onDone){
    var L = +p.dataset.len; if (!(L>0)) { L = p.getTotalLength(); p.dataset.len = L; }
    if (reduced || !(dur>1)){ p.style.strokeDashoffset = 0; if(onDone) onDone(); return null; }
    p.style.strokeDashoffset = L;
    var raf = 0, start = 0, cancelled = false;
    function frame(ts){
      if(cancelled) return;
      if(!start) start = ts;
      var t = clamp((ts-start)/dur, 0, 1);
      var e = t<0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2,3)/2;  // easeInOutCubic
      p.style.strokeDashoffset = (L*(1-e)).toFixed(2);
      if(t<1) raf = requestAnimationFrame(frame);
      else { p.style.strokeDashoffset = 0; if(onDone) onDone(); }
    }
    raf = requestAnimationFrame(frame);
    return { cancel:function(){ cancelled = true; if(raf) cancelAnimationFrame(raf); } };
  }
  // returns { play, step, showAll }
  function makeWriter(el, d, opts){
    opts = opts || {};
    var seqTimers=[], stepIdx=0, inkEls=[];
    if (!d.s){ // no stroke data: static glyph
      el.innerHTML = gridSVG() + '<div class="writer__static">'+d.ch+'</div>';
      return { play:function(){}, step:function(){}, showAll:function(){}, hasStrokes:false };
    }
    var n = d.s.length, cols = opts.rainbow ? palette(n) : null;
    var defs="", ghosts="", inks="";
    for(var i=0;i<n;i++){
      var col = cols?cols[i]:"var(--accent)";
      defs += '<clipPath id="cp'+i+'"><path d="'+d.s[i]+'"/></clipPath>';
      ghosts += '<path class="ghost" d="'+d.s[i]+'"/>';
      inks += '<path class="ink" data-i="'+i+'" d="'+medianPath(d.m[i])+'" fill="none" stroke="'+col+'" stroke-width="166" stroke-linecap="round" stroke-linejoin="round" clip-path="url(#cp'+i+')"/>';
    }
    var nums="";
    if (opts.numbers){
      layoutNumbers(d.m).forEach(function(p,i){
        var col = cols?cols[i]:"var(--accent)";
        nums += '<text x="'+p[0].toFixed(0)+'" y="'+p[1].toFixed(0)+'" text-anchor="middle" dominant-baseline="central" class="snum" fill="'+col+'">'+(i+1)+'</text>';
      });
    }
    el.innerHTML = gridSVG() +
      '<svg class="writer__char" viewBox="0 0 1024 1024" role="img" aria-label="'+d.ch+' stroke order">'+
      '<defs>'+defs+'</defs><g transform="translate(0,900) scale(1,-1)">'+ghosts+inks+'</g>'+
      '<g class="writer__nums">'+nums+'</g></svg>';
    inkEls = $all(".ink", el);
    inkEls.forEach(function(p){ var L=p.getTotalLength(); p.dataset.len=L; p.style.strokeDasharray=L; p.style.strokeDashoffset=L; });
    var speed = opts.speed || 1, tweens=[];

    function stopAll(){ tweens.forEach(function(t){ if(t&&t.cancel) t.cancel(); }); tweens=[]; seqTimers.forEach(clearTimeout); seqTimers=[]; }
    function showAll(){ stopAll(); inkEls.forEach(function(p){ p.style.strokeDashoffset=0; }); stepIdx=inkEls.length; }
    function play(){
      stopAll();
      inkEls.forEach(function(p){ p.style.strokeDashoffset=+p.dataset.len; });
      if (reduced){ showAll(); return; }
      var i=0; stepIdx=0;
      (function nextS(){
        if (i>=inkEls.length) return;
        var p=inkEls[i], L=+p.dataset.len, dur=clamp(220+L*0.34,320,900)/speed;
        stepIdx=i+1;
        tweens.push(tweenDash(p, dur, function(){ i++; seqTimers.push(setTimeout(nextS, 80/speed)); }));
      })();
    }
    function step(){
      stopAll();
      if (stepIdx>=inkEls.length){ inkEls.forEach(function(p){ p.style.strokeDashoffset=+p.dataset.len; }); stepIdx=0; }
      tweens.push(tweenDash(inkEls[stepIdx], reduced?1:460/speed));
      stepIdx++;
    }
    return { play:play, step:step, showAll:showAll, hasStrokes:true };
  }

  // ═════════ LEARN ═════════
  var learnWriter=null, traceCtx=null;
  function openLearn(deck, idx){
    nav.deck = deck; nav.idx = idx;
    var b = bandById(nav.band); applyAccent(b);
    renderLearn(true);
    showView("learn");
  }
  function renderLearn(animate){
    var d = nav.deck[nav.idx], bandId = nav.band;
    var opts = { rainbow:store.learn.rainbow, numbers:store.learn.numbers, speed:store.learn.speed };
    learnWriter = makeWriter($("#learn-writer"), d, opts);
    exitTrace();
    // header / info
    $("#learn-bigch").textContent = d.ch;
    $("#learn-py").textContent = d.py;
    $("#learn-en").textContent = d.en;
    var ri = radInfo(d.ch);
    $("#learn-radv").innerHTML = '<span class="rad-glyph zh">'+esc(ri.glyph||"—")+'</span>'+
      (ri.en ? '<span class="rad-mean">'+esc(ri.en)+(ri.cn?' · '+esc(ri.cn):'')+'</span>' : '');
    $("#learn-radnote").textContent = ri.note ? ('Often '+ri.note+'.') : '';
    $("#learn-strokes-v").textContent = d.strokes;
    $("#learn-order").textContent = d.strokes + (d.strokes>1?" strokes":" stroke") + (d.s?" · tap Step to build it one stroke at a time":" · stroke animation coming soon");
    $("#learn-radwrap").style.display = ri.glyph ? "" : "none";
    renderExtra(d);
    // know button
    var known = isKnown(bandId, d.ch);
    var kb = $("#learn-know");
    kb.classList.toggle("on", known);
    kb.querySelector(".st").textContent = known?"★":"☆";
    kb.querySelector(".lab").textContent = known?"I can write this":"Mark as learned";
    // position
    $("#learn-pos").textContent = pad2(nav.idx+1)+" / "+pad2(nav.deck.length);
    // top title
    var gu = unitOf(bandId, nav.unit);
    var lb = bandById(bandId);
    $("#learn-topttl").innerHTML = bandId==='GEN' ? ('General · '+esc(gu?gu.title:''))
      : (lb && lb.isLib) ? (esc(lb.name)+' · '+esc(gu?gu.title:''))
      : ("Book "+bandId.slice(1)+" · Unit "+nav.unit);
    syncLearnOpts();
    // mark seen
    if (animate!==false){ if (learnWriter.hasStrokes) requestAnimationFrame(learnWriter.play); }
    else learnWriter.showAll();
  }
  function pad2(n){ return (n<10?"0":"")+n; }
  // ── learn enrichment: 小故事 origin · 词语 word · 句子 sentence (shown when present) ──
  function rubySeg(seg, focus){
    return seg.map(function(p){ var ch=p[0],py=p[1];
      if(!py) return '<span class="punc">'+ch+'</span>';
      return '<ruby class="'+(ch===focus?'foc':'')+'">'+ch+'<rt>'+py+'</rt></ruby>'; }).join('');
  }
  function segText(seg){ return seg.map(function(p){return p[0];}).join(''); }
  function renderExtra(d){
    var x = extraOf(d.ch) || {}, html='';
    if (x.origin){ html += '<div class="lx"><span class="lx__lbl">小故事 · The story behind it</span><p class="lx__story">'+esc(x.origin)+'</p></div>'; }
    if (x.word){ html += '<div class="lx"><span class="lx__lbl">词语 · A word you can use</span>'+
      '<div class="lx__wordrow"><span class="lx__word zh">'+x.word.w+'</span>'+
      '<button class="saybtn" data-say="word" data-key="'+x.word.w+'" aria-label="Play word">🔊</button>'+
      '<span class="lx__wordmeta"><i>'+x.word.py+'</i> · '+esc(x.word.en)+'</span></div></div>'; }
    if (x.sentence){ html += '<div class="lx"><span class="lx__lbl">句子 · In a sentence</span>'+
      '<p class="lx__sent zh">'+rubySeg(x.sentence.seg, d.ch)+
      '<button class="saybtn" data-say="sentence" data-key="'+segText(x.sentence.seg)+'" aria-label="Play sentence">🔊</button></p>'+
      '<p class="lx__senten">'+esc(x.sentence.en)+'</p>'+
      (x.sentence.src ? '<p class="lx__sentsrc">— '+esc(x.sentence.src)+'</p>' : '')+'</div>'; }
    var box=$("#learn-extra"); if(!box) return;
    box.innerHTML=html; box.style.display = html?'':'none';
    $all('.saybtn', box).forEach(function(b){ b.addEventListener('click', function(){ playAudio(b.dataset.say, b.dataset.key); }); });
  }
  function learnGo(delta){
    nav.idx = (nav.idx + delta + nav.deck.length) % nav.deck.length;
    renderLearn(true);
  }
  function toggleKnow(){
    var d = nav.deck[nav.idx], k = keyOf(nav.band, d.ch);
    if (store.mastery[k]) delete store.mastery[k]; else store.mastery[k]=true;
    save(); renderLearn(false);
  }
  function syncLearnOpts(){
    $("#opt-rainbow").classList.toggle("is-on", store.learn.rainbow);
    $("#opt-numbers").classList.toggle("is-on", store.learn.numbers);
    var hide = !nav.deck[nav.idx].s;
    $("#learn-strokectls").style.opacity = hide?".4":"1";
    $("#learn-strokectls").style.pointerEvents = hide?"none":"auto";
  }
  function setLearnOpt(key,val){ store.learn[key]=val; save(); renderLearn(false); }

  // finger-trace canvas (per-stroke undo + a "watch the strokes" guide)
  var tracing=false, drawing=false, traceStrokes=[], curStroke=null, watchTimer=null;
  function accentCol(){ return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim()||"#C2473C"; }
  function sizeTrace(){
    var cv=$("#trace-canvas"), wrap=$("#learn-writerwrap");
    var dpr=window.devicePixelRatio||1, w=wrap.clientWidth, h=wrap.clientHeight;
    cv.width=w*dpr; cv.height=h*dpr; traceCtx=cv.getContext("2d");
    traceCtx.setTransform(dpr,0,0,dpr,0,0); traceCtx.lineCap="round"; traceCtx.lineJoin="round";
  }
  function wipeTrace(){ if(!traceCtx) return; var cv=$("#trace-canvas"); traceCtx.save(); traceCtx.setTransform(1,0,0,1,0,0); traceCtx.clearRect(0,0,cv.width,cv.height); traceCtx.restore(); }
  function redrawTrace(){
    if(!traceCtx) return; wipeTrace();
    traceCtx.strokeStyle=accentCol(); traceCtx.lineWidth=18; traceCtx.globalAlpha=.9;
    traceStrokes.forEach(function(s){ if(!s.length) return;
      traceCtx.beginPath(); traceCtx.moveTo(s[0][0],s[0][1]);
      for(var i=1;i<s.length;i++) traceCtx.lineTo(s[i][0],s[i][1]);
      if(s.length===1) traceCtx.lineTo(s[0][0]+0.1,s[0][1]+0.1);
      traceCtx.stroke(); });
  }
  function enterTrace(){
    tracing=true; $("#learn-writerwrap").classList.add("tracing"); $("#learn-trace").classList.add("is-on");
    traceStrokes=[]; sizeTrace(); redrawTrace();
  }
  function exitTrace(){
    tracing=false; stopWatch(); $("#learn-writerwrap").classList.remove("tracing"); $("#learn-trace").classList.remove("is-on");
    traceStrokes=[]; wipeTrace();
  }
  function clearTrace(){ traceStrokes=[]; redrawTrace(); }
  function undoTrace(){ traceStrokes.pop(); redrawTrace(); }
  function stopWatch(){ $("#learn-writerwrap").classList.remove("watching"); if(watchTimer){ clearTimeout(watchTimer); watchTimer=null; } }
  function traceXY(e){ var cv=$("#trace-canvas"), r=cv.getBoundingClientRect(); return [e.clientX-r.left, e.clientY-r.top]; }
  function bindTrace(){
    var cv = $("#trace-canvas");
    function down(e){ if(!tracing)return; e.preventDefault(); stopWatch(); drawing=true; curStroke=[traceXY(e)]; traceStrokes.push(curStroke); redrawTrace(); }
    function move(e){ if(!tracing||!drawing)return; e.preventDefault(); curStroke.push(traceXY(e)); redrawTrace(); }
    function up(){ drawing=false; curStroke=null; }
    cv.addEventListener("pointerdown",down); cv.addEventListener("pointermove",move);
    window.addEventListener("pointerup",up); window.addEventListener("pointercancel",up);
  }

  // shuffle — shared with the Exercises module via STUDIO
  function shuffle(a){ a=a.slice(); for(var i=a.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)); var t=a[i]; a[i]=a[j]; a[j]=t; } return a; }

  // ═════════ INIT ═════════
  function init(){
    bindAuth(); bindTrace(); buildGenBand(); buildGenThemes();
    buildIndex(); buildLibrary();
    // resume an existing session (cookie), else show the login/signup form
    if (API_BASE){
      api("/api/me").then(function(res){
        if (res.ok){ session = res.body; afterLogin(); } else showView("lock");
      }).catch(function(){ showView("lock"); });
    } else {
      showView("lock");
    }

    // nav buttons
    $("#home-lock").addEventListener("click", lockApp);
    $("#units-back").addEventListener("click", function(){ applyAccent(null); buildHome(); showView("home"); });
    $("#deck-back").addEventListener("click", function(){ openBand(nav.band); });
    $("#learn-back").addEventListener("click", function(){ openUnit(nav.band, nav.unit); });


    // learn controls
    $("#learn-replay").addEventListener("click", function(){ if(learnWriter) learnWriter.play(); });
    $("#learn-step").addEventListener("click", function(){ if(learnWriter) learnWriter.step(); });
    $("#opt-rainbow").addEventListener("click", function(){ setLearnOpt("rainbow", !store.learn.rainbow); });
    $("#opt-numbers").addEventListener("click", function(){ setLearnOpt("numbers", !store.learn.numbers); });
    $("#learn-prev").addEventListener("click", function(){ learnGo(-1); });
    $("#learn-next").addEventListener("click", function(){ learnGo(1); });
    $("#learn-know").addEventListener("click", toggleKnow);
    $("#learn-trace").addEventListener("click", function(){ if(tracing) exitTrace(); else if(nav.deck[nav.idx].s) enterTrace(); });
    $("#learn-clear").addEventListener("click", clearTrace);
    $("#learn-undo").addEventListener("click", undoTrace);
    $("#learn-exercises").addEventListener("click", function(){ window.Exercises && window.Exercises.start({bandId:nav.band, unit:nav.unit}); });

    // deck → exercises hub (flashcards removed)
    $("#deck-exercises").addEventListener("click", function(){ window.Exercises && window.Exercises.start({bandId:nav.band, unit:nav.unit}); });
    $("#units-practice").addEventListener("click", function(){ window.Exercises && window.Exercises.start({bandId:nav.band}); });
    // big-character audio (stub)
    var sayBtn=$("#learn-say"); if(sayBtn) sayBtn.addEventListener("click", function(){ if(nav.deck[nav.idx]) playAudio('char', nav.deck[nav.idx].ch); });

    // keyboard for learn/practice
    document.addEventListener("keydown", function(e){
      if ($("#view-learn").classList.contains("is-active")){
        if (e.key==="ArrowRight"){ e.preventDefault(); learnGo(1); }
        else if (e.key==="ArrowLeft"){ e.preventDefault(); learnGo(-1); }
        else if (e.key===" "){ e.preventDefault(); if(learnWriter) learnWriter.play(); }
      }
    });
  }
  // expose helpers for the Exercises module (learn/exercises.js)
  window.STUDIO = {
    makeWriter: makeWriter, bandById: bandById, applyAccent: applyAccent,
    showView: showView, openUnit: openUnit, openBand: openBand,
    esc: esc, shuffle: shuffle, palette: palette,
    extra: EXTRA, extraOf: extraOf, playAudio: playAudio, charIndex: CHAR_INDEX,
    gridSVG: gridSVG, medianPath: medianPath, rubySeg: rubySeg, segText: segText,
    strokeMatch: strokeMatch, tweenDash: tweenDash
  };

  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
