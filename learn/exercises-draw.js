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
  function trace(c, body, onDone, S){
    body.innerHTML =
      '<div class="ex-ask">Write <b class="zh" style="font-size:1.3em">'+c.ch+'</b> over the faint guide. <span class="ex-sub">Stay on the lines.</span></div>'+
      '<div class="ex-orderwrap">'+
        '<div class="writer ex-orderboard" id="ex-traceboard">'+ S.gridSVG() +
          '<svg class="ex-draw-svg" viewBox="0 0 1024 1024"><g transform="translate(0,900) scale(1,-1)">'+ghostPaths(c,S)+
          '<g class="ex-reveal-ink" style="display:none">'+inkPaths(c,S)+'</g></g></svg>'+
          '<canvas class="ex-drawcanvas" id="ex-tracecanvas"></canvas>'+
        '</div>'+
        '<div class="ex-drawbar">'+
          '<button class="ctl" id="ex-trace-undo">↶ Undo</button>'+
          '<button class="ctl" id="ex-trace-clear">Clear</button>'+
          '<button class="ctl primary" id="ex-trace-check">Check ✓</button>'+
        '</div>'+
      '</div>';
    var board = $("#ex-traceboard"), cv = $("#ex-tracecanvas"), ctx, strokes = [], cur = null, drawing = false, done = false;
    function size(){
      var dpr = window.devicePixelRatio||1, w = board.clientWidth, h = board.clientHeight;
      cv.width = w*dpr; cv.height = h*dpr; ctx = cv.getContext("2d");
      ctx.setTransform(dpr,0,0,dpr,0,0); ctx.lineCap="round"; ctx.lineJoin="round"; redraw();
    }
    function redraw(){
      if(!ctx) return; ctx.clearRect(0,0,cv.width,cv.height);
      ctx.strokeStyle=accentCol(); ctx.lineWidth=20; ctx.globalAlpha=.92;
      strokes.forEach(function(s){ if(!s.length) return; ctx.beginPath(); ctx.moveTo(s[0][0],s[0][1]);
        for(var i=1;i<s.length;i++) ctx.lineTo(s[i][0],s[i][1]); if(s.length===1) ctx.lineTo(s[0][0]+.1,s[0][1]+.1); ctx.stroke(); });
    }
    function xy(e){ var r=cv.getBoundingClientRect(); return [e.clientX-r.left, e.clientY-r.top]; }
    function down(e){ if(done) return; e.preventDefault(); drawing=true; cur=[xy(e)]; strokes.push(cur); redraw(); }
    function move(e){ if(done||!drawing) return; e.preventDefault(); cur.push(xy(e)); redraw(); }
    function up(){ drawing=false; cur=null; }
    cv.addEventListener("pointerdown",down); cv.addEventListener("pointermove",move);
    window.addEventListener("pointerup",up); window.addEventListener("pointercancel",up);
    $("#ex-trace-undo").addEventListener("click", function(){ if(done)return; strokes.pop(); redraw(); });
    $("#ex-trace-clear").addEventListener("click", function(){ if(done)return; strokes=[]; redraw(); });
    $("#ex-trace-check").addEventListener("click", check);
    requestAnimationFrame(size);

    function check(){
      if(done) return; done=true;
      var W=board.clientWidth, H=board.clientHeight, R=94;
      var pts=[]; strokes.forEach(function(s){ s.forEach(function(p){ pts.push([p[0]*1024/W, 900 - p[1]*1024/H]); }); });
      var covered=0, total=0;
      c.m.forEach(function(med){ med.forEach(function(mp){ total++;
        for(var i=0;i<pts.length;i++){ var dx=pts[i][0]-mp[0], dy=pts[i][1]-mp[1]; if(dx*dx+dy*dy<=R*R){ covered++; break; } } }); });
      var cov = total? covered/total : 0, pct = Math.round(cov*100), n=c.s.length;
      $(".ex-reveal-ink", board).style.display = "";   // reveal correct strokes
      cv.style.opacity = ".4"; cv.style.pointerEvents="none";
      $("#ex-trace-check").style.display="none"; $("#ex-trace-undo").disabled=true; $("#ex-trace-clear").disabled=true;
      var ok = cov >= 0.6 && strokes.length >= 1;
      var msg = ok ? ('Nice tracing — '+pct+'% on the lines.')
                   : (strokes.length===0 ? 'Draw over the guide, then Check.' : 'Keep on the lines — '+pct+'% covered. The strokes are shown now.');
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
        cv.style.opacity=".45"; $("#ex-struct-reveal").textContent="That\u2019s "+c.ch;
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
