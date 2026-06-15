/* exercises.js — 学写字 · Character Studio · Exercises.
   A skill-labelled Exercise HUB (听 Listen · 读 Read · 写 Write) replaces the old
   flashcards. Each card runs ONE focused exercise; "Mixed" blends them.
     听 listen   — 听音选字 listen & choose (audio stub)
     读 read     — 认拼音 pinyin · 认意思 meaning · 找汉字 char · 连一连 match
                   组词 build-a-word · 选字填空 fill-the-blank
     写 write    — 数笔画 strokes · 部首 radical · 笔顺 order
                   描红 trace · 结构 build-the-shape  (in exercises-draw.js)
   Data-driven from STUDIO (CHAR_INDEX, CONTENT_EXTRA). Harder distractors:
   pinyin prefers same initial; characters prefer same radical.                */
(function () {
  "use strict";
  var S, sess = null, answered = false, cleanOrder = true, hubScope = null;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $all = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  function pick(a){ return a[Math.floor(Math.random()*a.length)]; }
  function uniq(a){ var o=[],seen={}; a.forEach(function(x){ if(x!=null && !seen[x]){seen[x]=1;o.push(x);} }); return o; }
  var CHEERS = ['对了！','很好！','太棒了！','Nice!'];

  // ───────── exercise catalogue ─────────
  var SKILL = {
    mix:{zh:'综合', en:'Mixed', col:'var(--accent)'},
    listen:{zh:'听', en:'Listen', col:'#B07A2E'},
    read:{zh:'读', en:'Read', col:'#3E7C8C'},
    write:{zh:'写', en:'Write', col:'var(--accent)'}
  };
  var EXS = [
    {id:'mixed',  skill:'mix',    zh:'综合练习', en:'Mixed practice',   desc:'A balanced set across reading and writing.'},
    {id:'listen', skill:'listen', zh:'听音选字', en:'Listen & choose',  desc:'Hear it, then pick the right character.', audio:true},
    {id:'pinyin', skill:'read',   zh:'认拼音',   en:'Pick the pinyin',  desc:'See a character, choose how it sounds.'},
    {id:'meaning',skill:'read',   zh:'认意思',   en:'Pick the meaning', desc:'See a character, choose what it means.'},
    {id:'char',   skill:'read',   zh:'找汉字',   en:'Find the character',desc:'From pinyin and meaning, pick the character.'},
    {id:'word',   skill:'read',   zh:'组词',     en:'Build a word',     desc:'Choose the character that completes the word.', need:'word'},
    {id:'fill',   skill:'read',   zh:'选字填空', en:'Fill in the blank',desc:'Choose the character that fits the sentence.', need:'sentence'},
    {id:'match',  skill:'read',   zh:'连一连',   en:'Match the pairs',  desc:'Match each character to its pinyin.'},
    {id:'strokes',skill:'write',  zh:'数笔画',   en:'Count the strokes',desc:'How many strokes does it take to write?'},
    {id:'radical',skill:'write',  zh:'部首',     en:'Find the radical', desc:'Pick the radical (部首) of the character.', need:'radical'},
    {id:'order',  skill:'write',  zh:'笔顺',     en:'Stroke order',     desc:'Tap the strokes in writing order.', need:'s'},
    {id:'trace',  skill:'write',  zh:'描红',     en:'Trace it',         desc:'Write over the guide — checked for you.', need:'s'},
    {id:'structure',skill:'write',zh:'结构',     en:'Build the shape',  desc:'Recall the structure, sketch it, then compare.', need:'struct'}
  ];
  function specById(id){ return EXS.filter(function(e){return e.id===id;})[0]; }

  // ───────── scope helpers ─────────
  function collectChars(scope){
    var b=S.bandById(scope.bandId), out=[];
    b.units.forEach(function(u){ if(scope.unit && u.n!==scope.unit) return; u.chars.forEach(function(c){ out.push(c); }); });
    return out;
  }
  function poolOf(scope){ var b=S.bandById(scope.bandId), out=[]; b.units.forEach(function(u){ u.chars.forEach(function(c){ out.push(c); }); }); return out; }
  function ex(ch){ return S.extra[ch] || null; }
  function segHas(sent, ch){ return sent && sent.seg && sent.seg.some(function(p){ return p[0]===ch; }); }
  function qualifies(spec, c){
    if(spec.need==='word')     return !!(ex(c.ch)&&ex(c.ch).word);
    if(spec.need==='sentence') return !!(ex(c.ch)&&ex(c.ch).sentence&&segHas(ex(c.ch).sentence,c.ch));
    if(spec.need==='struct')   return !!(ex(c.ch)&&ex(c.ch).struct);
    if(spec.need==='radical')  return !!c.radical;
    if(spec.need==='s')        return !!c.s;
    return true;
  }
  function qcount(spec, chars){
    if(spec.id==='mixed') return chars.length;
    if(spec.id==='match') return chars.length>=3 ? chars.length : 0;
    return chars.filter(function(c){ return qualifies(spec,c); }).length;
  }
  function reasonFor(spec){
    if(spec.need==='word')     return 'Add a word in the library to unlock';
    if(spec.need==='sentence') return 'Add an example sentence to unlock';
    if(spec.need==='struct')   return 'Add a structure tag to unlock';
    if(spec.id==='match')      return 'Needs at least 3 characters';
    return 'Not available for these characters';
  }

  // ═════════ HUB ═════════
  function start(scope){ openHub(scope); }
  function openHub(scope){
    S = window.STUDIO; var b = S.bandById(scope.bandId); S.applyAccent(b);
    hubScope = scope;
    var chars = collectChars(scope);
    var lbl;
    if (scope.bandId==='GEN'){ var gu=b.units.filter(function(u){return u.n===scope.unit;})[0]; lbl = scope.unit ? gu.title : 'General Characters'; }
    else if (b.isLib){ var lu=b.units.filter(function(u){return u.n===scope.unit;})[0]; lbl = scope.unit ? (lu?lu.title:b.name) : b.name; }
    else lbl = scope.unit ? ("Unit "+scope.unit) : ("Book "+scope.bandId.slice(1)+" · "+b.name);
    $("#exh-title").innerHTML = lbl + ' <span class="zh">练习</span>';
    $("#exh-count").innerHTML = '<b>'+chars.length+'</b> characters';
    var groups = [['listen','听 Listening'],['read','读 Reading'],['write','写 Writing']];
    var html = '<div class="exhub-mixed">'+ card(specById('mixed'), chars) +'</div>';
    groups.forEach(function(g){
      var cards = EXS.filter(function(e){ return e.skill===g[0]; }).map(function(e){ return card(e, chars); }).join('');
      html += '<div class="exhub-group"><div class="exhub-glabel" style="--sk:'+SKILL[g[0]].col+'">'+g[1]+'</div><div class="exhub-grid">'+cards+'</div></div>';
    });
    $("#exh-groups").innerHTML = html;
    $all('.excard', $("#exh-groups")).forEach(function(btn){
      if(btn.classList.contains('is-off')) return;
      btn.addEventListener('click', function(){ runSession(scope, btn.dataset.ex); });
    });
    S.showView('exhub');
  }
  function capFor(id, n){
    if(id==='match') return n;
    if(id==='mixed') return Math.min(13, n*3);
    if(id==='trace'||id==='structure') return Math.min(6, n);
    if(id==='order'||id==='listen') return Math.min(8, n);
    return Math.min(10, n);
  }
  function card(spec, chars){
    var n = qcount(spec, chars), off = n===0, sk = SKILL[spec.skill];
    var q = capFor(spec.id, n);
    var foot = off ? '<span class="excard__off">'+reasonFor(spec)+'</span>'
                   : '<span class="excard__go">'+(spec.id==='match'?'warm-up':q+' question'+(q>1?'s':''))+' <i>›</i></span>';
    var mixed = spec.id==='mixed';
    return '<button class="excard'+(mixed?' excard--mixed':'')+(off?' is-off':'')+'" data-ex="'+spec.id+'"'+(off?' disabled':'')+' style="--sk:'+sk.col+'">'+
      '<span class="excard__skill">'+sk.zh+' '+sk.en+'</span>'+
      '<span class="excard__ttl"><span class="excard__zh zh">'+spec.zh+'</span><span class="excard__en">'+spec.en+'</span></span>'+
      '<span class="excard__desc">'+spec.desc+(spec.audio?' <span class="excard__stub">🔊 audio soon</span>':'')+'</span>'+
      '<span class="excard__foot">'+foot+'</span></button>';
  }

  // ═════════ SESSION ═════════
  function runSession(scope, typeId){
    var chars = collectChars(scope), pool = poolOf(scope), spec = specById(typeId), queue;
    if (typeId==='mixed') queue = buildMixed(chars);
    else if (typeId==='match') queue = [{t:'match', items:S.shuffle(chars).slice(0, Math.min(5, chars.length))}];
    else {
      var qs = chars.filter(function(c){ return qualifies(spec,c); }).map(function(c){ return {t:typeId, c:c}; });
      qs = S.shuffle(qs);
      var cap = (typeId==='trace'||typeId==='structure') ? 6 : (typeId==='order'||typeId==='listen') ? 8 : 10;
      queue = qs.slice(0, cap);
    }
    sess = { scope:scope, type:typeId, chars:chars, pool:pool, queue:queue, idx:0, score:0,
      scoredTotal: queue.filter(function(q){ return q.t!=='match'; }).length, spec:spec };
    $("#ex-title").innerHTML = (specById(typeId).zh) + ' <span class="zh" style="opacity:.6;font-size:.8em">'+specById(typeId).en+'</span>';
    $("#ex-result").style.display="none"; $("#ex-stage").style.display="flex";
    render(); S.showView("exercises");
  }
  function buildMixed(chars){
    var qs=[];
    chars.forEach(function(c){ qs.push({t:'pinyin',c:c}); qs.push({t:'meaning',c:c}); qs.push({t:'char',c:c}); });
    chars.forEach(function(c,i){ if(i%2===0) qs.push({t:'strokes',c:c}); });
    chars.forEach(function(c,i){ if(i%3===1 && c.radical) qs.push({t:'radical',c:c}); });
    chars.forEach(function(c){ if(ex(c.ch)&&ex(c.ch).word) qs.push({t:'word',c:c}); });
    chars.forEach(function(c){ if(ex(c.ch)&&ex(c.ch).sentence&&segHas(ex(c.ch).sentence,c.ch)) qs.push({t:'fill',c:c}); });
    S.shuffle(chars.filter(function(c){return c.s;})).slice(0,2).forEach(function(c){ qs.push({t:'order',c:c}); });
    qs = S.shuffle(qs).slice(0,12);
    var warm = chars.length>=3 ? [{t:'match', items:S.shuffle(chars).slice(0, Math.min(5, chars.length))}] : [];
    return warm.concat(qs);
  }

  // ───────── distractors (harder) ─────────
  function opts(correct, ds){ return S.shuffle([{v:correct,correct:true}].concat(ds.map(function(d){return {v:d,correct:false};}))); }
  function toneless(p){ return (p||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,'').toLowerCase(); }
  function initialOf(p){ var b=toneless(p), m=b.match(/^(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])/); return m?m[1]:(b[0]||''); }
  function pinyinOpts(c){
    var others = uniq(sess.pool.map(function(x){return x.py;})).filter(function(p){return p!==c.py;});
    var ci=initialOf(c.py);
    var same = S.shuffle(others.filter(function(p){return initialOf(p)===ci;}));
    var rest = S.shuffle(others.filter(function(p){return initialOf(p)!==ci;}));
    return opts(c.py, same.concat(rest).slice(0,3));
  }
  function meaningOpts(c){ var o=uniq(sess.pool.map(function(x){return x.en;})).filter(function(p){return p!==c.en;}); return opts(c.en, S.shuffle(o).slice(0,3)); }
  function charOpts(c){
    var others = sess.pool.filter(function(x){ return x.ch!==c.ch; });
    var same = S.shuffle(others.filter(function(x){ return x.radical && x.radical===c.radical; })).map(function(x){return x.ch;});
    var rest = S.shuffle(uniq(others.map(function(x){return x.ch;})).filter(function(ch){ return same.indexOf(ch)<0; }));
    return opts(c.ch, uniq(same.concat(rest)).slice(0,3));
  }
  function radicalOpts(c){
    var o=uniq(sess.pool.map(function(x){return x.radical;}).filter(function(r){return r && r!==c.radical;}));
    o=uniq(o.concat(['口','人','女','日','木','水','心','一','十','亻'])).filter(function(r){return r!==c.radical;});
    return opts(c.radical, S.shuffle(o).slice(0,3));
  }
  function strokeOpts(c){
    var n=c.strokes, seen={}; seen[n]=1; var ds=[];
    S.shuffle([n-1,n+1,n-2,n+2,n+3,n-3,n+4]).forEach(function(x){ if(x>0 && !seen[x] && ds.length<3){ seen[x]=1; ds.push(x); } });
    while(ds.length<3){ var r=Math.max(1,n+(Math.floor(Math.random()*7)-3)); if(!seen[r]){ seen[r]=1; ds.push(r); } }
    return opts(String(n), ds.map(String));
  }

  // ───────── render dispatch ─────────
  function render(){
    var q = sess.queue[sess.idx]; if(!q) return finish();
    answered=false; cleanOrder=true;
    $("#ex-next").style.display="none";
    var f=$("#ex-feedback"); f.className="ex-feedback"; f.innerHTML="";
    $("#ex-card").classList.remove("answered");
    updateHud(q);
    $("#ex-kind").innerHTML = kindLabel(q.t);
    var body=$("#ex-body");
    if (q.t==='match')  return renderMatch(q, body);
    if (q.t==='order')  return renderOrder(q.c, body);
    if (q.t==='listen') return renderListen(q.c, body);
    if (q.t==='word')   return renderWord(q.c, body);
    if (q.t==='fill')   return renderFill(q.c, body);
    if (q.t==='trace')  return window.ExercisesDraw.trace(q.c, body, function(ok,msg){ answered=true; graded(ok, ok?null:msg, false, msg); }, S);
    if (q.t==='structure') return window.ExercisesDraw.structure(q.c, body, function(ok,msg){ answered=true; graded(ok, ok?msg:msg, false, msg); }, S);
    renderMCQ(q, body);
  }
  function kindLabel(t){
    var spec = specById(t==='match'?'match':t) || {}; var sk = SKILL[spec.skill||'read'];
    return '<span class="ex-skilltag" style="--sk:'+sk.col+'">'+sk.zh+' '+sk.en+'</span>'+spec.zh+' · '+spec.en;
  }
  function updateHud(q){
    var seen = sess.queue.slice(0,sess.idx).filter(function(x){return x.t!=='match';}).length;
    $("#ex-steps").textContent = q.t==='match' ? 'Warm-up' : ('Q '+(seen+1)+' / '+sess.scoredTotal);
    $("#ex-score").innerHTML = '★ <b>'+sess.score+'</b>';
    $("#ex-track-i").style.width = (sess.idx/sess.queue.length*100).toFixed(1)+'%';
  }

  // ───────── MCQ ─────────
  function renderMCQ(q, body){
    var c=q.c, prompt="", options, big=false;
    if (q.t==='pinyin'){ prompt='<div class="ex-bigch zh">'+c.ch+'</div><div class="ex-ask">Which pinyin is this?</div>'; options=pinyinOpts(c); }
    else if (q.t==='meaning'){ prompt='<div class="ex-bigch zh">'+c.ch+'</div><div class="ex-ask">What does it mean?</div>'; options=meaningOpts(c); }
    else if (q.t==='strokes'){ prompt='<div class="ex-bigch zh">'+c.ch+'</div><div class="ex-ask">How many strokes?</div>'; options=strokeOpts(c); }
    else if (q.t==='radical'){ prompt='<div class="ex-bigch zh">'+c.ch+'</div><div class="ex-ask">Which part is the radical (部首)?</div>'; options=radicalOpts(c); big='zh'; }
    else if (q.t==='char'){ prompt='<div class="ex-prompt2"><span class="ex-py">'+c.py+'</span><span class="ex-en">'+S.esc(c.en)+'</span></div><div class="ex-ask">Which character?</div>'; options=charOpts(c); big='zh'; }
    var optCls = (q.t==='char'||q.t==='radical') ? ' ex-opt--zh' : (q.t==='strokes' ? ' ex-opt--num' : '');
    body.innerHTML = prompt + '<div class="ex-options'+(optCls?' wide':'')+'">'+
      options.map(function(o,i){ return '<button class="ex-opt'+optCls+'" data-i="'+i+'">'+(big==='zh'?'<span class="zh">'+o.v+'</span>':S.esc(o.v))+'</button>'; }).join('') +'</div>';
    bindOpts(body, options, q, c);
  }
  function bindOpts(body, options, q, c, answerText){
    $all('.ex-opt', body).forEach(function(btn){
      btn.addEventListener('click', function(){
        if(answered) return; answered=true;
        var ok = options[+btn.dataset.i].correct;
        $all('.ex-opt', body).forEach(function(b,j){ b.classList.add('locked'); if(options[j].correct) b.classList.add('correct'); });
        if(!ok) btn.classList.add('wrong');
        var at = answerText || ((q.t==='char'||q.t==='radical') ? (q.t==='radical'? c.ch+' = '+c.radical : 'It\u2019s '+c.ch) :
                 (q.t==='strokes'? c.strokes+' strokes' : (q.t==='pinyin'? c.py : c.en)));
        graded(ok, 'Answer: '+at);
      });
    });
  }

  // ───────── 听音选字 listen & choose ─────────
  function renderListen(c, body){
    var options = charOpts(c);
    body.innerHTML = '<button class="ex-listenbtn" id="ex-listen-play" aria-label="Play sound">🔊</button>'+
      '<div class="ex-ask">Listen, then tap the character you heard. <span class="ex-sub">(audio coming soon)</span></div>'+
      '<div class="ex-options wide">'+options.map(function(o,i){ return '<button class="ex-opt ex-opt--zh" data-i="'+i+'"><span class="zh">'+o.v+'</span></button>'; }).join('')+'</div>';
    $("#ex-listen-play").addEventListener('click', function(){ S.playAudio('char', c.ch); });
    setTimeout(function(){ S.playAudio('char', c.ch); }, 250);
    bindOpts(body, options, {t:'listen'}, c, c.py+' · '+S.esc(c.en)+' = '+c.ch);
  }

  // ───────── 组词 build a word ───────── (blank the headword char in its word)
  function renderWord(c, body){
    var w = ex(c.ch).word, blanked = w.w.replace(c.ch, '◯');
    var options = charOpts(c);
    body.innerHTML = '<div class="ex-wordprompt"><span class="ex-wordpy">'+w.py+'</span><span class="ex-worden">'+S.esc(w.en)+'</span>'+
      '<div class="ex-wordblank zh">'+blanked+'</div></div>'+
      '<div class="ex-ask">Which character completes the word?</div>'+
      '<div class="ex-options wide">'+options.map(function(o,i){ return '<button class="ex-opt ex-opt--zh" data-i="'+i+'"><span class="zh">'+o.v+'</span></button>'; }).join('')+'</div>';
    bindOpts(body, options, {t:'word'}, c, w.w+' · '+w.py);
  }

  // ───────── 选字填空 fill in the blank ─────────
  function renderFill(c, body){
    var sent = ex(c.ch).sentence;
    var html = sent.seg.map(function(p){ var ch=p[0], py=p[1];
      if(ch===c.ch) return '<span class="ex-fillgap">?</span>';
      if(!py) return '<span class="punc">'+ch+'</span>';
      return '<ruby>'+ch+'<rt>'+py+'</rt></ruby>'; }).join('');
    var options = charOpts(c);
    body.innerHTML = '<div class="ex-ask">Which character fits the blank?</div>'+
      '<p class="ex-fillsent zh">'+html+'</p><p class="ex-fillen">'+S.esc(sent.en)+'</p>'+
      '<div class="ex-options wide">'+options.map(function(o,i){ return '<button class="ex-opt ex-opt--zh" data-i="'+i+'"><span class="zh">'+o.v+'</span></button>'; }).join('')+'</div>';
    bindOpts(body, options, {t:'fill'}, c, 'It\u2019s '+c.ch+' ('+c.py+')');
  }

  // ───────── 笔顺 stroke order tap ─────────
  function renderOrder(c, body){
    var paths = c.s.map(function(p,i){ return '<path class="ex-stroke" data-i="'+i+'" d="'+p+'"/>'; }).join('');
    body.innerHTML = '<div class="ex-ask">Tap the strokes <b>in writing order</b> — first to last.</div>'+
      '<div class="ex-orderwrap"><div class="writer ex-orderboard">'+ S.gridSVG() +
      '<svg class="ex-order-svg" viewBox="0 0 1024 1024"><g transform="translate(0,900) scale(1,-1)">'+paths+'</g></svg></div>'+
      '<button class="ctl ex-hint" id="ex-hint">✨ Hint</button></div>';
    var n=c.s.length, expected=0, strokes=$all('.ex-stroke', body), cols=S.palette(n);
    function tap(i){
      if(answered) return; var el=strokes[i]; if(el.classList.contains('done')) return;
      if(i===expected){ el.classList.add('done'); el.style.fill=cols[i]; expected++;
        if(expected===n){ answered=true; graded(cleanOrder, cleanOrder?null:'Watch the order again in Learn.'); } }
      else { cleanOrder=false; el.classList.add('bad'); setTimeout(function(){ el.classList.remove('bad'); },420); }
    }
    strokes.forEach(function(el){ el.addEventListener('click', function(){ tap(+el.dataset.i); }); });
    $("#ex-hint", body).addEventListener('click', function(){ if(answered||expected>=n) return; var el=strokes[expected]; el.classList.add('hint'); setTimeout(function(){ el.classList.remove('hint'); },700); });
  }

  // ───────── 连一连 match ─────────
  function renderMatch(q, body){
    var items=q.items, left=items.slice(), right=S.shuffle(items.slice());
    body.innerHTML = '<div class="ex-ask">Match each character with its pinyin.</div>'+
      '<div class="ex-match"><div class="ex-col">'+left.map(function(c){ return '<button class="ex-pair zh" data-ch="'+c.ch+'" data-col="ch">'+c.ch+'</button>'; }).join('')+'</div>'+
      '<div class="ex-col">'+right.map(function(c){ return '<button class="ex-pair" data-ch="'+c.ch+'" data-col="py">'+c.py+'</button>'; }).join('')+'</div></div>';
    var sel=null, matched=0;
    function deselect(){ if(sel){ sel.classList.remove('sel'); sel=null; } }
    function flash(el){ el.classList.add('bad'); setTimeout(function(){ el.classList.remove('bad'); },420); }
    $all('.ex-pair', body).forEach(function(btn){
      btn.addEventListener('click', function(){
        if(btn.classList.contains('done')) return;
        if(!sel){ sel=btn; btn.classList.add('sel'); return; }
        if(sel===btn){ deselect(); return; }
        if(sel.dataset.col===btn.dataset.col){ deselect(); sel=btn; btn.classList.add('sel'); return; }
        if(sel.dataset.ch===btn.dataset.ch){ sel.classList.add('done'); btn.classList.add('done'); sel.classList.remove('sel'); sel=null; matched++;
          if(matched===items.length){ answered=true; graded(true, null, true); } }
        else { flash(btn); flash(sel); deselect(); }
      });
    });
  }

  // ───────── grading + flow ─────────
  function graded(ok, answerText, isMatch){
    $("#ex-card").classList.add("answered");
    if (!isMatch && sess.queue[sess.idx].t!=='match'){ if(ok) sess.score++; }
    var f=$("#ex-feedback"); f.className='ex-feedback '+(ok?'ok':'no');
    f.innerHTML = ok ? ('<span class="fi">✓</span> '+(isMatch?'All matched — nice!':(answerText||pick(CHEERS))))
                     : ('<span class="fi">✕</span> '+(answerText||'Not quite'));
    $("#ex-score").innerHTML='★ <b>'+sess.score+'</b>';
    var nx=$("#ex-next"); nx.style.display="inline-flex";
    nx.innerHTML = (sess.idx>=sess.queue.length-1 ? 'See results' : 'Next') + ' <span class="ic">›</span>';
  }
  function next(){ sess.idx++; render(); }
  function finish(){
    $("#ex-stage").style.display="none";
    var res=$("#ex-result"); res.style.display="flex";
    var pct = sess.scoredTotal ? Math.round(sess.score/sess.scoredTotal*100) : 100;
    var ring=$("#ex-ring"); ring.style.background='conic-gradient(var(--accent) '+pct+'%, var(--line-soft) 0)';
    ring.innerHTML='<span class="ex-ring-in"><b>'+sess.score+'</b><small>/ '+sess.scoredTotal+'</small></span>';
    $("#ex-result-h").textContent = pct>=90 ? 'Outstanding! 太棒了' : pct>=60 ? 'Well done! 很好' : 'Good effort — keep going!';
    $("#ex-result-sub").textContent = pct>=90 ? 'You really know these characters.' : pct>=60 ? 'A few to review — try another exercise.' : 'Practise the strokes in Learn, then try again.';
  }

  function exitToChars(){ var s=hubScope||sess.scope; if(s.unit) S.openUnit(s.bandId, s.unit); else S.openBand(s.bandId); }

  function init(){
    $("#ex-next").addEventListener('click', next);
    $("#ex-again").addEventListener('click', function(){ runSession(sess.scope, sess.type); });
    $("#ex-done").addEventListener('click', function(){ exitToChars(); });
    $("#ex-back").addEventListener('click', function(){ openHub(sess.scope); });
    var hb=$("#exh-back"); if(hb) hb.addEventListener('click', exitToChars);
    document.addEventListener('keydown', function(e){
      if (!$("#view-exercises").classList.contains('is-active')) return;
      if ((e.key==='Enter'||e.key==='ArrowRight') && $("#ex-next").style.display!=='none'){ e.preventDefault(); next(); }
    });
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', init); else init();
  window.Exercises = { start:start };
})();
