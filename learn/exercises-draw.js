/* exercises-draw.js — 学写字 · Character Studio · writing-skill exercises.
   Two hands-on writing tasks, used by the Exercise Hub (exercises.js):
     描红 Trace it     — write over the faint guide; coverage is auto-checked.
     结构 Build shape  — recall the character's overall structure (auto-graded),
                         then free-sketch each part and reveal the real character.
   Exposes window.ExercisesDraw = { trace, structure }.
   Each takes (c, body, onDone, S):  c = char object, body = container element,
   onDone(ok, message) reports the scored result, S = window.STUDIO.            */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $all = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  function accentCol(){ return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#C2473C"; }

  // ───────── shared board ─────────
  function ghostPaths(c, S){ return c.s.map(function(p){ return '<path class="g-ghost" d="'+p+'"/>'; }).join(''); }
  function inkPaths(c, S){
    var cols = S.palette(c.s.length);
    return c.m.map(function(m,i){ return '<path class="g-ink" data-i="'+i+'" d="'+S.medianPath(m)+
      '" fill="none" stroke="'+cols[i]+'" stroke-width="150" stroke-linecap="round" stroke-linejoin="round"/>'; }).join('');
  }

  // ═════════ 描红 TRACE ═════════
  // Real stroke-by-stroke handwriting recognition (S.strokeMatch): every drawn
  // stroke is checked for shape, position, direction and order. Correct strokes
  // are inked in; wrong ones flash and prompt a targeted tip, with the expected
  // stroke shown as a hint after repeated misses. Score = first-try accuracy.
  var SVGNS = "http://www.w3.org/2000/svg";
  function trace(c, body, onDone, S){
    var n = c.s.length, cols = S.palette(n);
    body.innerHTML =
      '<div class="ex-ask">Write <b class="zh" style="font-size:1.3em">'+c.ch+'</b> stroke by stroke. <span class="ex-sub">Follow the order — each stroke is checked.</span></div>'+
      '<div class="ex-orderwrap">'+
        '<div class="writer ex-orderboard" id="ex-traceboard">'+ S.gridSVG() +
          '<svg class="ex-draw-svg" viewBox="0 0 1024 1024"><g transform="translate(0,900) scale(1,-1)">'+
            ghostPaths(c,S)+
            '<g class="ex-trace-done"></g>'+
            '<g class="ex-trace-hint"></g>'+
          '</g></svg>'+
          '<canvas class="ex-drawcanvas" id="ex-tracecanvas"></canvas>'+
        '</div>'+
        '<div class="ex-traceprog" id="ex-traceprog"></div>'+
        '<div class="ex-drawbar">'+
          '<button class="ctl" id="ex-trace-hintbtn">Show this stroke</button>'+
        '</div>'+
      '</div>';
    var board=$("#ex-traceboard"), cv=$("#ex-tracecanvas"), ctx;
    var doneG=$(".ex-trace-done",board), hintG=$(".ex-trace-hint",board), prog=$("#ex-traceprog");
    var curIdx=0, firstTry=0, mistakes=[], cur=null, drawing=false, done=false;
    for(var k=0;k<n;k++) mistakes.push(0);

    function size(){ var dpr=window.devicePixelRatio||1,w=board.clientWidth,h=board.clientHeight;
      cv.width=w*dpr; cv.height=h*dpr; ctx=cv.getContext("2d"); ctx.setTransform(dpr,0,0,dpr,0,0);
      ctx.lineCap="round"; ctx.lineJoin="round"; drawCur(); }
    function drawCur(){ if(!ctx) return; ctx.clearRect(0,0,cv.width,cv.height); if(!cur||!cur.length) return;
      ctx.strokeStyle=accentCol(); ctx.lineWidth=20; ctx.globalAlpha=.92; ctx.beginPath(); ctx.moveTo(cur[0][0],cur[0][1]);
      for(var i=1;i<cur.length;i++) ctx.lineTo(cur[i][0],cur[i][1]); if(cur.length===1) ctx.lineTo(cur[0][0]+.1,cur[0][1]+.1); ctx.stroke(); }
    function xy(e){ var r=cv.getBoundingClientRect(); return [e.clientX-r.left, e.clientY-r.top]; }
    function toData(p){ var W=board.clientWidth, H=board.clientHeight; return [p[0]*1024/W, 900 - p[1]*1024/H]; }
    function setProg(){ if(!done) prog.innerHTML = 'Stroke <b>'+(curIdx+1)+'</b> of '+n; }
    function clearHint(){ hintG.innerHTML=""; }
    function inkInto(g, i, dur, cls){
      var p=document.createElementNS(SVGNS,'path');
      p.setAttribute('class',cls); p.setAttribute('d',S.medianPath(c.m[i])); p.setAttribute('fill','none');
      p.setAttribute('stroke',cols[i]); p.setAttribute('stroke-width','150');
      p.setAttribute('stroke-linecap','round'); p.setAttribute('stroke-linejoin','round'); g.appendChild(p);
      var L=p.getTotalLength(); p.style.strokeDasharray=L; p.style.strokeDashoffset=L;
      p.animate([{strokeDashoffset:L},{strokeDashoffset:0}],{duration:dur,easing:'cubic-bezier(.45,.05,.3,1)',fill:'forwards'});
    }
    function showHint(manual){ clearHint(); inkInto(hintG, curIdx, 560, 'g-ink-hint');
      if(manual && mistakes[curIdx]===0) mistakes[curIdx]=1; }   // using the hint forfeits first-try credit
    function flash(ok){ board.classList.remove('ex-flash-ok','ex-flash-no'); void board.offsetWidth;
      board.classList.add(ok?'ex-flash-ok':'ex-flash-no'); }

    function commit(){
      var raw=cur; cur=null; drawCur();
      if(!raw || raw.length<1) return;
      var v=S.strokeMatch(raw.map(toData), c.m[curIdx], {});
      if(v.match){
        if(mistakes[curIdx]===0) firstTry++;
        clearHint(); inkInto(doneG, curIdx, 340, 'g-ink-done'); flash(true);
        curIdx++; if(curIdx>=n) return finish(); setProg();
      } else {
        mistakes[curIdx]++; flash(false);
        var tip = v.reason==='start' ? 'start it in the right place'
                : v.reason==='end' ? 'end it where the stroke finishes'
                : v.reason==='direction' ? 'check the stroke direction'
                : v.reason==='length' ? 'cover the whole stroke'
                : 'follow the stroke shape';
        prog.innerHTML = 'Stroke <b>'+(curIdx+1)+'</b> of '+n+' — not quite, '+tip+'.';
        if(mistakes[curIdx]>=2) showHint(false);
      }
    }

    function down(e){ if(done) return; e.preventDefault(); clearHint(); drawing=true; cur=[xy(e)]; drawCur(); }
    function move(e){ if(done||!drawing) return; e.preventDefault(); cur.push(xy(e)); drawCur(); }
    function up(){ if(done||!drawing) return; drawing=false; commit(); }
    cv.addEventListener("pointerdown",down); cv.addEventListener("pointermove",move);
    window.addEventListener("pointerup",up); window.addEventListener("pointercancel",up);
    $("#ex-trace-hintbtn").addEventListener("click", function(){ if(!done) showHint(true); });
    setProg(); requestAnimationFrame(size);

    function finish(){
      done=true; cv.style.pointerEvents="none"; clearHint(); $("#ex-trace-hintbtn").disabled=true;
      var pct=Math.round(100*firstTry/n), ok=firstTry/n>=0.5;
      prog.innerHTML = '✓ '+c.ch+' complete — '+firstTry+' / '+n+' strokes right first try ('+pct+'%).';
      var msg = ok ? ('Well written — '+firstTry+'/'+n+' strokes correct first try.')
                   : ('Completed — '+firstTry+'/'+n+' first try. Keep practising the order.');
      onDone(ok, msg, pct);
    }
  }

  // ═════════ 结构 STRUCTURE ═════════
  var STR = {
    single:{zh:'独体', en:'Single piece'},
    lr:{zh:'左右', en:'Left · right'},
    tb:{zh:'上下', en:'Top · bottom'},
    lmr:{zh:'左中右', en:'Three columns'},
    tmb:{zh:'上中下', en:'Three rows'},
    sw:{zh:'半包围', en:'Part-enclosed'},
    full:{zh:'全包围', en:'Enclosed'}
  };
  function diagram(type){
    var s = '<svg viewBox="0 0 40 40" class="strdia">';
    var f='none', st='currentColor', sw=2.4, r=3;
    function box(x,y,w,h){ return '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="'+r+'" fill="'+f+'" stroke="'+st+'" stroke-width="'+sw+'"/>'; }
    if(type==='single') s+=box(8,8,24,24);
    else if(type==='lr') s+=box(6,8,13,24)+box(21,8,13,24);
    else if(type==='tb') s+=box(8,6,24,13)+box(8,21,24,13);
    else if(type==='lmr') s+=box(4,9,10,22)+box(15,9,10,22)+box(26,9,10,22);
    else if(type==='tmb') s+=box(9,4,22,10)+box(9,15,22,10)+box(9,26,22,10);
    else if(type==='sw') s+='<path d="M32 8 H10 a2 2 0 0 0 -2 2 V32" fill="none" stroke="'+st+'" stroke-width="'+sw+'" stroke-linecap="round"/>'+box(18,18,12,12);
    else if(type==='full') s+=box(7,7,26,26)+box(15,15,10,10);
    return s+'</svg>';
  }
  function structure(c, body, onDone, S){
    var correct = (S.extra[c.ch]||{}).struct; if(!correct){ onDone(true,''); return; }
    var keys = Object.keys(STR), pool = S.shuffle(keys.filter(function(k){return k!==correct;})).slice(0,3);
    var optKeys = S.shuffle([correct].concat(pool));
    var word = (S.extra[c.ch]||{}).word;
    body.innerHTML =
      '<div class="ex-struct-prompt">'+
        '<div class="ex-prompt2"><span class="ex-py">'+c.py+'</span><span class="ex-en">'+S.esc(c.en)+'</span>'+
          '<button class="saybtn" id="ex-struct-say" aria-label="Play">🔊</button></div>'+
        '<div class="ex-ask">First — what is this character\u2019s <b>overall shape</b>?</div>'+
      '</div>'+
      '<div class="ex-structopts">'+ optKeys.map(function(k){
        return '<button class="structopt" data-k="'+k+'">'+diagram(k)+'<span class="structopt__zh zh">'+STR[k].zh+'</span><span class="structopt__en">'+STR[k].en+'</span></button>';
      }).join('') +'</div>'+
      '<div class="ex-structdraw" id="ex-structdraw" style="display:none"></div>';
    var sb=$("#ex-struct-say"); if(sb) sb.addEventListener("click", function(){ S.playAudio('char', c.ch); });
    var picked=false;
    $all('.structopt', body).forEach(function(btn){
      btn.addEventListener('click', function(){
        if(picked) return; picked=true;
        var ok = btn.dataset.k===correct;
        $all('.structopt', body).forEach(function(b){ b.classList.add('locked'); if(b.dataset.k===correct) b.classList.add('correct'); });
        if(!ok) btn.classList.add('wrong');
        revealDraw(ok);
        onDone(ok, ok ? ('Right — '+STR[correct].zh+' ('+STR[correct].en+').') : ('It\u2019s '+STR[correct].zh+' · '+STR[correct].en+'.'));
      });
    });

    function revealDraw(ok){
      var wrap=$("#ex-structdraw"); wrap.style.display="";
      wrap.innerHTML =
        '<div class="ex-struct-step">Now sketch each part from memory — then reveal to compare. <span class="ex-sub">Shape matters, not stroke order.</span></div>'+
        '<div class="ex-orderwrap"><div class="writer ex-orderboard ex-structboard" id="ex-structboard">'+ S.gridSVG() +
          '<svg class="ex-struct-region" viewBox="0 0 100 100">'+regions(correct)+'</svg>'+
          '<svg class="ex-draw-svg ex-struct-real" viewBox="0 0 1024 1024" style="display:none"><g transform="translate(0,900) scale(1,-1)">'+inkPaths(c,S)+'</g></svg>'+
          '<canvas class="ex-drawcanvas" id="ex-structcanvas"></canvas>'+
        '</div>'+
        '<div class="ex-drawbar">'+
          '<button class="ctl" id="ex-struct-clear">Clear</button>'+
          '<button class="ctl primary" id="ex-struct-reveal">Reveal &amp; compare</button>'+
        '</div></div>';
      var board=$("#ex-structboard"), cv=$("#ex-structcanvas"), ctx, strokes=[], cur=null, drawing=false;
      function sz(){ var dpr=window.devicePixelRatio||1,w=board.clientWidth,h=board.clientHeight; cv.width=w*dpr;cv.height=h*dpr;ctx=cv.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.lineCap="round";ctx.lineJoin="round";rd(); }
      function rd(){ if(!ctx)return; ctx.clearRect(0,0,cv.width,cv.height); ctx.strokeStyle=accentCol(); ctx.lineWidth=18; ctx.globalAlpha=.9;
        strokes.forEach(function(s){ if(!s.length)return; ctx.beginPath();ctx.moveTo(s[0][0],s[0][1]); for(var i=1;i<s.length;i++)ctx.lineTo(s[i][0],s[i][1]); if(s.length===1)ctx.lineTo(s[0][0]+.1,s[0][1]+.1); ctx.stroke(); }); }
      function xy(e){ var r=cv.getBoundingClientRect(); return [e.clientX-r.left,e.clientY-r.top]; }
      cv.addEventListener("pointerdown",function(e){ e.preventDefault();drawing=true;cur=[xy(e)];strokes.push(cur);rd(); });
      cv.addEventListener("pointermove",function(e){ if(!drawing)return;e.preventDefault();cur.push(xy(e));rd(); });
      window.addEventListener("pointerup",function(){drawing=false;cur=null;}); window.addEventListener("pointercancel",function(){drawing=false;cur=null;});
      $("#ex-struct-clear").addEventListener("click",function(){ strokes=[]; rd(); });
      $("#ex-struct-reveal").addEventListener("click",function(){
        $(".ex-struct-real", board).style.display=""; $(".ex-struct-region", board).style.opacity=".25";
        cv.style.opacity=".45";
        // real recognition: how many of the character's strokes did the sketch capture?
        // Order- and direction-independent (free sketch), so each median is matched once.
        var W=board.clientWidth, H=board.clientHeight, used=[], hit=0, m=c.m.length;
        for(var z=0;z<m;z++) used.push(false);
        strokes.forEach(function(s){
          if(s.length<2) return;
          var pts=s.map(function(p){ return [p[0]*1024/W, 900 - p[1]*1024/H]; });
          var best=-1, bestFr=1;
          for(var i=0;i<m;i++){ if(used[i]) continue;
            var v=S.strokeMatch(pts, c.m[i], {anyDir:true, dir:-1, frechet:0.42, startEnd:0.34});
            if(v.match && v.frechet<bestFr){ bestFr=v.frechet; best=i; } }
          if(best>=0){ used[best]=true; hit++; }
        });
        var pct=Math.round(100*hit/m), grade=document.createElement('div'); grade.className='ex-struct-grade';
        grade.innerHTML = strokes.length
          ? ('Your sketch matched <b>'+hit+'</b> of '+m+' strokes ('+pct+'%) \u2014 compare with '+c.ch+'.')
          : ('Sketch the parts next time. This is '+c.ch+'.');
        wrap.appendChild(grade);
        $("#ex-struct-reveal").textContent="That\u2019s "+c.ch;
        $("#ex-struct-reveal").classList.remove("primary"); $("#ex-struct-reveal").disabled=true;
      });
      requestAnimationFrame(sz);
    }
  }
  // light dashed region guides per structure (viewBox 100x100)
  function regions(type){
    var a='stroke="currentColor" stroke-width="1.4" stroke-dasharray="4 4" fill="none" opacity=".5"';
    function L(x1,y1,x2,y2){ return '<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" '+a+'/>'; }
    if(type==='lr') return L(50,8,50,92);
    if(type==='tb') return L(8,50,92,50);
    if(type==='lmr') return L(36,8,36,92)+L(64,8,64,92);
    if(type==='tmb') return L(8,36,92,36)+L(8,64,92,64);
    if(type==='sw') return '<path d="M70 14 H22 a4 4 0 0 0 -4 4 V78" '+a+'/>';
    if(type==='full') return '<rect x="26" y="26" width="48" height="48" '+a+'/>';
    return '';
  }

  window.ExercisesDraw = { trace: trace, structure: structure, STR: STR };
})();
