/* 史案 — 史书知识图谱阅读器 · data layer (window.SHI_DATA)
 *
 * This is the *shape* the production system must generalise (see the design
 * handoff). Two principles are baked into the structure on purpose:
 *
 *   1. Sourced data is the product. Every ENTITIES record carries provenance
 *      (`src`) and cross-references (`seen`). These are the trust contract —
 *      the UI marks any entity WITHOUT a `src` as 未溯源 (unverified) rather
 *      than silently presenting it as fact.
 *
 *   2. One passage today, the whole canon tomorrow. Nothing here assumes a
 *      single hardcoded text: ENTITIES is a *global registry* keyed by a
 *      canonical id, and PASSAGES is a collection whose lines reference the
 *      registry by id («entityId» knowledge layer · ⟨langId⟩ language layer).
 *      A real build replaces these literals with an API-backed store and a
 *      cross-text (互见) engine; the rendering engine should not need to change.
 */
(function () {
  // ── category metadata (知识层 / 專名) — colour + underline texture ──
  // Texture lets a category stay distinguishable even with colour off.
  const CATS = {
    person: { label: '人物', color: '#B23A2B', deco: 'solid' },
    place:  { label: '地名', color: '#2C7A70', deco: 'wavy' },
    office: { label: '官职', color: '#3F6B8C', deco: 'double' },
    era:    { label: '年号', color: '#B26B00', deco: 'dotted' },
    rank:   { label: '爵位', color: '#6C5AA6', deco: 'dashed' }
  };

  // ── grammar-role colours (语言层) — dashed underline in all cases ──
  const LANG_ROLES = {
    '句式': '#B23A2B',
    '副词': '#3F6B8C',
    '活用': '#B0772A',
    '代词': '#6C5AA6',
    '介词': '#2C7A70'
  };

  // ── global entity registry ──
  // id → { w, cat, brief, fields:[{k,v}], src, seen:[chapter…] }
  // The `今比` field, when present, is the 现代类比 (modern-analogy) anchor the
  // detail dock leads with. `src` is MANDATORY for a verified entity.
  const ENTITIES = {
    shuofang: {
      w: '朔方', cat: 'place', brief: '今内蒙古杭锦旗一带',
      fields: [
        { k: '今地', v: '今内蒙古杭锦旗、磴口一带' },
        { k: '沿革', v: '汉武帝元朔二年（前127）置朔方郡，为北边军镇重地' },
        { k: '辨', v: '本传两说并存——「朔方人，或云雁门人」，籍贯本不确定' }
      ],
      src: '《读史方舆纪要》卷61', seen: ['梁书·武帝纪', '南史·侯景传']
    },
    yanmen: {
      w: '雁門', cat: 'place', brief: '今山西代县一带',
      fields: [
        { k: '今地', v: '今山西忻州代县' },
        { k: '形胜', v: '雁门关所在，历代北疆第一要塞' }
      ],
      src: '《元和郡县图志》河东道', seen: ['南史·侯景传']
    },
    zhenbing: {
      w: '北鎮戍兵', cat: 'office', brief: '北魏六镇的边防戍卒',
      fields: [
        { k: '性质', v: '北魏沿边六镇（沃野、怀朔、武川等）的戍防军士' },
        { k: '处境', v: '六镇本为拱卫旧都的精锐；孝文迁都洛阳后地位骤降、待遇沉沦，终酿「六镇之乱」' },
        { k: '今比', v: '边防戍卒 · 起于行伍的最底层' }
      ],
      src: '《魏书·官氏志》·六镇考', seen: ['魏书·广阳王深传', '北史·尔朱荣传']
    },
    gerong: {
      w: '葛榮', cat: 'person', brief: '北魏六镇起义军领袖',
      fields: [
        { k: '身份', v: '六镇之乱后期起义军首领，自称天子，国号齐' },
        { k: '结局', v: '528年滏口之战为尔朱荣所擒杀' },
        { k: '关系', v: '侯景随尔朱荣讨平葛荣，以此战之功受擢——是其发迹的起点' }
      ],
      src: '《魏书·卷九八·葛荣传》', seen: ['北史·尔朱荣传', '资治通鉴·梁纪']
    },
    erzhurong: {
      w: '爾朱榮', cat: 'person', brief: '北魏权臣 · 天柱大将军 · 493–530',
      fields: [
        { k: '生卒', v: '493–530' },
        { k: '身份', v: '北魏末契胡军阀，官至天柱大将军，一度执掌朝政' },
        { k: '大事', v: '河阴之变（沉杀太后及朝臣两千余人）、平定葛荣' },
        { k: '关系', v: '侯景归附的第一位重要军阀，其军旅生涯由此起步' }
      ],
      src: '《魏书·卷七四·尔朱荣传》', seen: ['北史·尔朱荣传', '梁书·侯景传', '资治通鉴·梁纪']
    },
    dingzhou: {
      w: '定州刺史', cat: 'office', brief: '定州（今河北定州）最高长官',
      fields: [
        { k: '辖区', v: '定州，治今河北定州' },
        { k: '职权', v: '州级最高长官，常加都督、行台衔，军政一把抓' },
        { k: '品级', v: '约正三品（北魏制）' },
        { k: '今比', v: '省长兼省军区主官' }
      ],
      src: '《通典·职官·州牧刺史》', seen: ['魏书·地形志']
    },
    daxingtai: {
      w: '大行臺', cat: 'office', brief: '总揽一方军政的中央派出长官',
      fields: [
        { k: '性质', v: '「行台」为尚书台派往地方、总领数州军政的最高机构，「大行台」为其长官' },
        { k: '职权', v: '集军、政、财于一身，权倾一方' },
        { k: '今比', v: '战区 + 大区行政首长' }
      ],
      src: '《通典·职官·行台省》', seen: ['北齐书·神武纪']
    },
    puyang: {
      w: '濮陽郡公', cat: 'rank', brief: '郡公爵 · 封地濮阳',
      fields: [
        { k: '爵等', v: '郡公——位在县公之上、郡王之下' },
        { k: '封地', v: '濮阳郡，今河南濮阳一带' },
        { k: '意味', v: '由戍卒至开国郡公，可见其骤贵之速' }
      ],
      src: '《隋书·百官志》·爵制', seen: []
    },
    gaohuan: {
      w: '高歡', cat: 'person', brief: '东魏权臣 · 北齐奠基者 · 496–547',
      fields: [
        { k: '生卒', v: '496–547，谥神武皇帝' },
        { k: '身份', v: '东魏实际掌权者，北齐高氏王朝奠基人' },
        { k: '大事', v: '灭尔朱氏、立东魏、与西魏宇文泰长期对峙' },
        { k: '关系', v: '侯景转投高欢，受任专制河南；高欢一死，侯景即叛' }
      ],
      src: '《北齐书·卷一·神武纪》', seen: ['魏书·孝静帝纪', '梁书·侯景传', '南史·贼臣传']
    },
    henan: {
      w: '河南', cat: 'place', brief: '黄河以南诸州 · 侯景拥兵之地',
      fields: [
        { k: '范围', v: '此处指黄河以南、东魏所辖十三州之地' },
        { k: '战略', v: '介于东魏、西魏、南梁之间，是侯景拥兵自重、待价而沽的本钱' }
      ],
      src: '《资治通鉴·梁纪十六》', seen: ['梁书·武帝纪', '南史·侯景传']
    },
    wuding5: {
      w: '武定五年', cat: 'era', brief: '公元547年 · 东魏孝静帝',
      fields: [
        { k: '公元', v: '547年' },
        { k: '在位', v: '东魏孝静帝元善见，实权在高欢、高澄父子' },
        { k: '大事', v: '是年高欢卒；侯景举河南叛东魏，先降西魏复降南梁——乱局之始' }
      ],
      src: '《魏书·孝静帝纪》武定五年', seen: ['梁书·武帝纪', '资治通鉴·梁纪']
    },
    liangwu: {
      w: '梁武帝', cat: 'person', brief: '南朝梁开国皇帝萧衍 · 464–549',
      fields: [
        { k: '生卒', v: '464–549' },
        { k: '在位', v: '502–549，南梁开国之君' },
        { k: '大事', v: '崇佛，四度舍身同泰寺；晚年纳侯景，终致「侯景之乱」，饿死台城' },
        { k: '关系', v: '接纳侯景来降、封河南王，埋下侯景之乱的祸根' }
      ],
      src: '《梁书·卷三·武帝纪下》', seen: ['南史·梁本纪', '梁书·侯景传']
    },
    henanwang: {
      w: '河南王', cat: 'rank', brief: '梁武帝封侯景的王爵',
      fields: [
        { k: '爵等', v: '王爵——异姓封王，殊礼' },
        { k: '用意', v: '梁武帝以高爵招纳，冀不战而收河南之地' }
      ],
      src: '《梁书·武帝纪》太清元年', seen: ['南史·侯景传']
    },
    dajiangjun: {
      w: '大將軍', cat: 'office', brief: '武官最高品级之一',
      fields: [
        { k: '品级', v: '一品重号将军，武职之极' },
        { k: '性质', v: '多为荣宠、统兵之号' }
      ],
      src: '《通典·职官·武官》', seen: []
    }
  };

  // ── language-layer tokens — context-specific reading (NOT the whole entry) ──
  const LANG = {
    jian:   { w: '見', role: '句式', sub: '被动',   roleFull: '被动标志',   gloss: '助动词，表被动，相当于「被」。「見憚鄉里」＝被乡里所忌惮。', src: '王力《古代汉语》·被动句' },
    shao:   { w: '稍', role: '副词', sub: '古义',   roleFull: '时间副词',   gloss: '古义为「渐渐、逐渐」，非今义「稍微」。「稍立功效」＝渐渐立下功劳。', src: '《古汉语常用字字典》' },
    zhuang: { w: '壯', role: '活用', sub: '意动',   roleFull: '意动用法',   gloss: '形容词意动：「以……为壮」，即赏识、看重。「甚壯之」＝很赏识他。', src: '王力《古代汉语》·词类活用' },
    qi:     { w: '器', role: '活用', sub: '名作动', roleFull: '名词作动词', gloss: '名词「器（才具）」用作动词：器重、看重。「器其才」＝看重他的才能。', src: '《古汉语常用字字典》' },
    zhi1:   { w: '之', role: '代词', sub: '第三人称', roleFull: '人称代词', gloss: '第三人称代词，作宾语，指代侯景。「壯之」＝赏识他。', src: '《古汉语虚词词典》' },
    zhi2:   { w: '之', role: '代词', sub: '第三人称', roleFull: '人称代词', gloss: '第三人称代词，指代侯景来降一事。「納之」＝接纳了他。', src: '《古汉语虚词词典》' },
    yi:     { w: '以', role: '介词', sub: '凭借/率', roleFull: '介词',      gloss: '介词，「率领、带着」。「以眾降歡」＝率部众投降高欢。', src: '《古汉语虚词词典》' }
  };

  // ── passages collection (one shipped; engine must not assume one) ──
  // `lines` reference the registry inline: «entityId» knowledge · ⟨langId⟩ language.
  // map / rel / rise describe the 传主 and belong to the passage. In production
  // they would be assembled cross-text (互見法) from many mentions.
  const PASSAGES = [{
    id: 'houjing-liangshu',
    title: '梁書·侯景傳',
    sub: '节选 · 唐 · 姚思廉 撰',
    seal: '侯',
    subject: '侯景',
    intro: '侯景本北镇戍卒，乘六镇之乱而起，辗转事尔朱荣、高欢，终以河南之地降梁复叛，酿成「侯景之乱」，南朝由是衰落。本段叙其出身与早年发迹之路。',
    lines: [
      '侯景，字萬景，«shuofang»人，或云«yanmen»人。少而不羈，⟨jian⟩憚鄉里。',
      '及長，驍勇有膂力，善騎射，以選為«zhenbing»，⟨shao⟩立功效。',
      '後與«gerong»戰，敗之，遂從«erzhurong»為先鋒。榮甚⟨zhuang⟩⟨zhi1⟩，擢為«dingzhou»、«daxingtai»，封«puyang»。',
      '及«gaohuan»誅爾朱氏，景⟨yi⟩眾降歡，仍為定州刺史。歡⟨qi⟩其才，授以兵柄，使擁眾十萬，專制«henan»。',
      '«wuding5»，歡卒，景懼禍，遂以河南十三州來降。«liangwu»納⟨zhi2⟩，封«henanwang»、«dajiangjun»，使持節。'
    ],

    // 地理视图 · 行迹。xy = 示意坐标(0–100)，非真实地理；route = 按时序连线的点 id。
    // alt:true = 学界存疑的地点。production → 县级经纬度 + 真实路线。
    map: {
      caption: '侯景行迹示意 · 北朝中后期 · 底图待接入真实地理坐标（县级精度）',
      points: [
        { id: 'shuofang', order: 1, xy: [24, 17], mod: '今内蒙古杭锦旗', note: '籍贯 · 起点（一说雁门）' },
        { id: 'yanmen',   order: 1, xy: [37, 27], mod: '今山西代县',     note: '一说籍贯 · 学界存疑', alt: true },
        { id: 'dingzhou', order: 2, xy: [57, 29], mod: '今河北定州',     note: '528 擢定州刺史' },
        { id: 'henan',    order: 3, xy: [50, 47], mod: '黄河以南十三州',  note: '530s 专制河南 · 拥众十万' },
        { id: 'jiankang', order: 4, xy: [67, 65], mod: '今江苏南京',     note: '547 举河南降梁所向 · 后陷台城', ref: 'liangwu' }
      ],
      route: ['shuofang', 'dingzhou', 'henan', 'jiankang']
    },

    // 人物关系视图 · 以传主为中心。xy = 节点示意坐标。
    rel: {
      center: { w: '侯景', sub: '本传主' },
      nodes: [
        { id: 'gerong',    w: '葛榮',   rel: '敌',     sub: '破之，以功受擢', xy: [20, 22] },
        { id: 'erzhurong', w: '爾朱榮', rel: '归附',   sub: '第一位军阀主公', xy: [80, 20] },
        { id: 'gaohuan',   w: '高歡',   rel: '归附→叛', sub: '授兵柄，旋叛',   xy: [82, 74] },
        { id: 'liangwu',   w: '梁武帝', rel: '降',     sub: '纳降，封河南王', xy: [18, 76] }
      ]
    },

    // 升迁 / 时间轴。rank = 官位高低(0–100)，时间轴的纵轴高度。ref = 关联专名。
    rise: [
      { year: '525',  tag: '起步', rank: 34, title: '北鎮戍兵',                ref: 'zhenbing', note: '以选为北镇戍卒，稍立功效——起于行伍最底层。' },
      { year: '528',  tag: '骤升', rank: 82, title: '定州刺史 · 大行臺 · 濮陽郡公', ref: 'dingzhou', note: '从尔朱荣讨平葛荣，以功一跃为州刺史、开国郡公。' },
      { year: '530s', tag: '高位', rank: 96, title: '專制河南 · 擁眾十萬',        ref: 'henan',    note: '转投高欢，受任专制河南，拥兵十万，俨然一方之雄。' },
      { year: '547',  tag: '转折', rank: 62, title: '舉河南來降',              ref: 'wuding5',  note: '高欢卒，景惧祸而叛；先降西魏，复以十三州降梁，封河南王。' },
      { year: '549',  tag: '后事', rank: 46, title: '陷臺城',                  ref: 'liangwu',  note: '侯景之乱爆发，梁武帝饿死台城，南朝盛极而衰。' }
    ]
  }];

  window.SHI_DATA = { CATS, LANG_ROLES, ENTITIES, LANG, PASSAGES };
})();
