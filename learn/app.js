/* app.js — 学写字 · Character Studio engine (vanilla, no deps).
   Lock → Home(bands) → Units → Deck → Learn / Practice.
   Stroke brush ported from the Casey character explorer (makemeahanzi 1024 Y-up). */
(function () {
  "use strict";
  var DATA = (window.APP_DATA && window.APP_DATA.bands) || [];
  var CLASS_CODE = "2580";
  var LS = "ccs-studio-v1", SS = "ccs-studio-unlock";
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
  function playAudio(kind, key){
    if (hasRecording(kind,key)){
      var a=new Audio('audio/'+kind+'/'+encodeURIComponent(key)+'.mp3');
      a.play().then(function(){ toast(key,'playing'); }).catch(function(){ if(speak(key)) toast(key,'read aloud'); });
    } else if (speak(key)){ toast(key,'read aloud'); }
    else { toast(key,'audio coming soon'); }
  }

  // ───────── persistence ─────────
  var store = { mastery:{}, learn:{ rainbow:true, numbers:true, speed:1, pinyin:true }, last:null };
  try { var s = JSON.parse(localStorage.getItem(LS)); if (s) store = Object.assign(store, s), store.learn = Object.assign({ rainbow:true, numbers:true, speed:1, pinyin:true }, s.learn||{}); } catch(e){}
  function save(){ try{ localStorage.setItem(LS, JSON.stringify(store)); }catch(e){} }
  function keyOf(band, ch){ return band + ":" + ch; }
  function isKnown(band, ch){ return !!store.mastery[keyOf(band,ch)]; }
  function masteredCount(bandId, unit){
    var b = bandById(bandId); var n = 0;
    b.units.forEach(function(u){ if (unit && u.n !== unit) return; u.chars.forEach(function(c){ if (isKnown(bandId, c.ch)) n++; }); });
    return n;
  }
  var GEN_BAND = null, LIB = {}, LIB_SERIES = [];
  function buildGenBand(){
    var G = (window.GENERAL_DATA && window.GENERAL_DATA.groups) || [];
    GEN_BAND = { id:'GEN', name:'General Characters', cnpy:[["通","tōng"],["用","yòng"],["汉","hàn"],["字","zì"],], isGen:true,
      glyph:'字', pigment:{glyph:'字', name:'Free practice'}, accent:'#3E7C8C', accentSoft:'#C2DBE1', tint:'#E6F0F3',
      total: G.reduce(function(s,g){ return s+g.chars.length; }, 0),
      units: G.map(function(g,i){ return { n:i+1, title:g.title, chars:g.chars }; }) };
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
      sub:'Common everyday characters, grouped by theme', books:[{
        id:'GEN', accent:GEN_BAND.accent, accentSoft:GEN_BAND.accentSoft, tint:GEN_BAND.tint, glyph:GEN_BAND.glyph, pigmentName:GEN_BAND.pigment.name,
        eyebrow:'Free practice', titleEn:'General Characters', cnpy:GEN_BAND.cnpy, unitWord:'themes', total:GEN_BAND.total, unitsLen:GEN_BAND.units.length }] });
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

  // ═════════ LOCK ═════════
  var entered = "";
  function renderDots(){
    $all("#lock-dots .d").forEach(function(d,i){ d.classList.toggle("on", i < entered.length); });
  }
  function pressKey(k){
    var lock = $(".lock"); lock.classList.remove("bad");
    if (k === "del"){ entered = entered.slice(0,-1); renderDots(); return; }
    if (entered.length >= 4) return;
    entered += k; renderDots();
    if (entered.length === 4){
      setTimeout(function(){
        if (entered === CLASS_CODE){ try{ sessionStorage.setItem(SS,"1"); }catch(e){} enterApp(); }
        else { lock.classList.add("bad"); navigator.vibrate && navigator.vibrate(120); setTimeout(function(){ entered=""; renderDots(); }, 380); }
      }, 140);
    }
  }
  function buildKeypad(){
    var pad = $("#keypad");
    var keys = ["1","2","3","4","5","6","7","8","9","clear","0","del"];
    pad.innerHTML = keys.map(function(k){
      if (k==="clear") return '<button class="key ghost" data-k="clear">Clear</button>';
      if (k==="del") return '<button class="key ghost" data-k="del">⌫</button>';
      return '<button class="key" data-k="'+k+'">'+k+'</button>';
    }).join("");
    pad.addEventListener("click", function(e){
      var btn = e.target.closest("[data-k]"); if (!btn) return;
      var k = btn.dataset.k;
      if (k==="clear"){ entered=""; renderDots(); $(".lock").classList.remove("bad"); }
      else pressKey(k);
    });
    document.addEventListener("keydown", function(e){
      if (!$("#view-lock").classList.contains("is-active")) return;
      if (/[0-9]/.test(e.key)) pressKey(e.key);
      else if (e.key === "Backspace") pressKey("del");
    });
  }

  function enterApp(){ applyAccent(null); buildHome(); showView("home"); }
  function lockApp(){ entered=""; renderDots(); try{ sessionStorage.removeItem(SS); }catch(e){} showView("lock"); }

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
  function buildHome(){
    var host = $("#home-sections");
    host.innerHTML = buildSections().map(function(sec){
      return '<section class="hsec">'+
        '<div class="hsec__head"><h2 class="hsec__title">'+esc(sec.en)+' <span class="zh">'+ruby(sec.cnpy)+'</span></h2>'+
        '<p class="hsec__sub">'+esc(sec.sub)+'</p></div>'+
        '<div class="bookgrid">'+ sec.books.map(bookCard).join('') +'</div></section>';
    }).join("");
    $all(".bookcard", host).forEach(function(c){ c.addEventListener("click", function(){ openBand(c.dataset.band); }); });
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
    var speed = opts.speed || 1;

    function showAll(){ inkEls.forEach(function(p){ (p.getAnimations()||[]).forEach(function(a){a.cancel();}); p.style.strokeDashoffset=0; }); stepIdx=inkEls.length; }
    function play(){
      seqTimers.forEach(clearTimeout); seqTimers=[];
      inkEls.forEach(function(p){ (p.getAnimations()||[]).forEach(function(a){a.cancel();}); p.style.strokeDashoffset=+p.dataset.len; });
      if (reduced){ showAll(); return; }
      stepIdx=0; var i=0;
      (function nextS(){
        if (i>=inkEls.length) return;
        var p=inkEls[i], L=+p.dataset.len, dur=clamp(220+L*0.34,320,900)/speed;
        p.animate([{strokeDashoffset:L},{strokeDashoffset:0}],{duration:dur,easing:"cubic-bezier(.45,.05,.3,1)",fill:"forwards"});
        i++; stepIdx=i; seqTimers.push(setTimeout(nextS, dur+80/speed));
      })();
    }
    function step(){
      seqTimers.forEach(clearTimeout); seqTimers=[];
      if (stepIdx>=inkEls.length){ inkEls.forEach(function(p){ p.style.strokeDashoffset=+p.dataset.len; }); stepIdx=0; }
      var p=inkEls[stepIdx], L=+p.dataset.len;
      p.animate([{strokeDashoffset:L},{strokeDashoffset:0}],{duration:reduced?1:460/speed,easing:"cubic-bezier(.45,.05,.3,1)",fill:"forwards"});
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
      '<p class="lx__senten">'+esc(x.sentence.en)+'</p></div>'; }
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
    buildKeypad(); renderDots(); bindTrace(); buildGenBand();
    buildIndex(); buildLibrary();
    // lock or enter
    var unlocked=false; try{ unlocked = sessionStorage.getItem(SS)==="1"; }catch(e){}
    if (unlocked) enterApp(); else showView("lock");

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
    gridSVG: gridSVG, medianPath: medianPath, rubySeg: rubySeg, segText: segText
  };

  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
